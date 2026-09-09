import discord
from discord.ext import commands, tasks
import sqlite3
from datetime import datetime, timedelta
from config import OWNER_IDS, admin_required, is_owner, Manage_messages_required, Manage_channels_required, replace_placeholders, save_json, load_json, GUILD_IDS
import json
import pytz
import traceback
DB_NAME = "reminders.db"


# ------------------ TIMEZONE DROPDOWN ------------------ #
TIMEZONES = [
    "UTC",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "Europe/London",
    "Europe/Berlin",
    "Asia/Tokyo"
]


def parse_time_flexible(t: str):
    from datetime import datetime

    t = t.strip().upper()

    # Try 12-hour format first (3:00 PM)
    try:
        return datetime.strptime(t, "%I:%M %p").strftime("%H:%M")
    except:
        pass

    # Try 24-hour format (15:00 or 03:00)
    try:
        return datetime.strptime(t, "%H:%M").strftime("%H:%M")
    except:
        pass

    raise ValueError(f"Invalid time format: {t}")


# ------------------ DB SETUP ------------------ #
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # reminders
    c.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        channel_id INTEGER,
        creator_id INTEGER,
        target_id INTEGER,
        message TEXT,
        times TEXT,
        timezone TEXT,
        last_triggered TEXT,
        completed INTEGER DEFAULT 0,
        one_time INTEGER DEFAULT 0,
        missed_count INTEGER DEFAULT 0
    )
    """)

    # points system
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_points (
        user_id INTEGER PRIMARY KEY,
        points INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()


class TimezoneSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=tz) for tz in TIMEZONES]
        super().__init__(placeholder="Select timezone", options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.timezone = self.values[0]
        await interaction.response.send_message(f"Timezone set to {self.values[0]} ✔️", ephemeral=True)


class TimezoneView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.timezone = None
        self.add_item(TimezoneSelect())


# ------------------ BUTTON ------------------ #
class ReminderView(discord.ui.View):
    def __init__(self, reminder_id, creator_id, target_id):
        super().__init__(timeout=None)
        self.reminder_id = reminder_id
        self.creator_id = creator_id
        self.target_id = target_id

    @discord.ui.button(label="✅ Done", style=discord.ButtonStyle.green)
    async def done_button(self, button, interaction: discord.Interaction):

        if interaction.user.id != self.target_id:
            return await interaction.response.send_message("Not your task ❗", ephemeral=True)

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        # ✅ CHECK if already completed
        c.execute("SELECT completed FROM reminders WHERE id = ?", (self.reminder_id,))
        row = c.fetchone()

        if not row or row[0] == 1:
            conn.close()
            return await interaction.response.send_message("Already completed ❗", ephemeral=True)

        # 🎯 GET POINT VALUE
        c.execute("SELECT reward_points FROM reminders WHERE id = ?", (self.reminder_id,))
        reward = c.fetchone()
        reward = reward[0] if reward and reward[0] else None

        if reward is None:
            import random
            reward = random.randint(10, 50)

        # ✅ mark complete
        c.execute("UPDATE reminders SET completed = 1 WHERE id = ?", (self.reminder_id,))

        # 💰 give points
        c.execute("""
        INSERT INTO user_points (user_id, points)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET points = points + ?
        """, (self.target_id, reward, reward))

        conn.commit()
        conn.close()

        # 🔥 DISABLE BUTTON
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(view=self)

        await interaction.followup.send(f"Completed! +{reward} points 💰", ephemeral=True)

        creator = interaction.guild.get_member(self.creator_id)
        if creator:
            await creator.send(f"{interaction.user.mention} completed their task! 🎉 (+{reward} pts)")






class Reminder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_db()
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()
        
    # LOOP
    @tasks.loop(seconds=30)
    async def check_reminders(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute("SELECT * FROM reminders WHERE completed = 0")
        reminders = c.fetchall()
        ##conn.commit()
        ##conn.close()
        

        try:
            c.execute("SELECT * FROM reminders WHERE completed = 0")
            reminders = c.fetchall()

            for r in reminders:
                (rid, guild_id, channel_id, creator_id, target_id,
                message, times_json, timezone, last_triggered,
                completed, one_time, missed_count) = r

                tz = pytz.timezone(timezone)
                now = datetime.now(tz)
                current_time_str = now.strftime("%H:%M")

                # SAFE TIMES
                try:
                    times = json.loads(times_json)
                    if not isinstance(times, list):
                        raise ValueError
                except:
                    print(f"[ERROR] Bad times for {rid}")
                    continue

                # SAFE last_triggered
                last = None
                last_time_str = None

                if last_triggered:
                    dt = datetime.fromisoformat(last_triggered)

                    if dt.tzinfo is None:
                        dt = pytz.utc.localize(dt)

                    last_dt = dt.astimezone(tz)

                    # ⏱️ get response time
                    c.execute("SELECT response_time FROM reminders WHERE id = ?", (rid,))
                    timeout = c.fetchone()[0] or 600

                    # ❗ if user didn't complete in time
                    if (now - last_dt).total_seconds() > timeout:

                        c.execute("SELECT completed FROM reminders WHERE id = ?", (rid,))
                        completed_flag = c.fetchone()[0]

                        if completed_flag == 0:
                            c.execute("""
                                UPDATE reminders
                                SET missed_count = missed_count + 1,
                                    strike_count = strike_count + 1
                                WHERE id = ?
                            """, (rid,))

                            print(f"[STRIKE] Reminder {rid} missed")

                            # prevent repeated strikes
                            c.execute("UPDATE reminders SET last_triggered = ? WHERE id = ?",
                                    (datetime.now(pytz.utc).isoformat(), rid))
                # 🔁 TRIGGER LOOP
                for t in times:

                    # 🔑 unique minute key (prevents duplicate firing)
                    current_minute_key = now.strftime("%Y-%m-%d %H:%M")

                    c.execute("SELECT last_fired_minute FROM reminders WHERE id = ?", (rid,))
                    last_fired_minute = c.fetchone()[0]

                    if last_fired_minute == current_minute_key:
                        continue
                    row = c.fetchone()
                    last_fired_minute = row[0] if row else None

                    # ⏱️ only trigger at correct time
                    if current_time_str != t:
                        continue

                    # 🚫 prevent duplicate trigger in same minute
                    if last_fired_minute == current_minute_key:
                        continue

                    guild = self.bot.get_guild(guild_id)
                    if not guild:
                        continue

                    channel = guild.get_channel(channel_id)
                    target = guild.get_member(target_id)

                    if channel and target:
                        view = ReminderView(rid, creator_id, target_id)

                        embed = discord.Embed(
                            title="⏰ Reminder",
                            description=message,
                            color=discord.Color.blurple()
                        )

                        embed.add_field(name="User", value=target.mention)
                        embed.add_field(name="Server", value=guild.name)
                        embed.add_field(name="Time", value=now.strftime("%I:%M %p"))

                        await channel.send(embed=embed, view=view)
                        c.execute(
                        "UPDATE reminders SET last_fired_minute = ? WHERE id = ?",
                        (current_minute_key, rid)
)
                    now_utc = datetime.now(pytz.utc).isoformat()

                    c.execute(
                        "UPDATE reminders SET last_triggered = ?, last_sent = ? WHERE id = ?",
                        (now_utc, now_utc, rid)
                    )

                    if one_time:
                        c.execute("UPDATE reminders SET completed = 1 WHERE id = ?", (rid,))

                # 🔥 STRIKE SYSTEM
                if last_triggered and not completed:
                    dt = datetime.fromisoformat(last_triggered)
                    if dt.tzinfo is None:
                        dt = pytz.utc.localize(dt)

                    last_dt = dt.astimezone(tz)

                    # ⏱️ 10 min timeout
                    if (now - last_dt).total_seconds() > 600:

                        # prevent duplicate strike
                        current_minute_key = now.strftime("%Y-%m-%d %H:%M")

                        c.execute("SELECT last_fired_minute FROM reminders WHERE id = ?", (rid,))
                        row = c.fetchone()
                        last_fired_minute = row[0] if row else None

                        # ✅ SAVE THAT IT FIRED
                        c.execute(
                            "UPDATE reminders SET last_fired_minute = ? WHERE id = ?",
                            (current_minute_key, rid)
                        )
                       
                        c.execute("""
                            UPDATE reminders 
                            SET missed_count = missed_count + 1,
                                strike_count = strike_count + 1
                            WHERE id = ?
                        """, (rid,))
                        
                        print(f"[STRIKE] User {target_id} missed reminder {rid}")
                conn.commit()
        finally:
            conn.close()

    @check_reminders.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

    # ------------------ SET REMINDER ------------------ #
    @discord.slash_command(name="set_reminder", description="Set a reminder for yourself or others", guild_ids=GUILD_IDS)
    async def set_reminder(
        self,
        interaction: discord.ApplicationContext, # type: ignore
        user: discord.Option(discord.Member),  # type: ignore
        message: discord.Option(str), # type: ignore
        times: discord.Option(str, "08:00,20:00"), # type: ignore
        one_time: discord.Option(bool, default=False), # type: ignore
        reward_points: discord.Option(int, required=False), # type: ignore
        response_time: discord.Option(int, required=False, description="Seconds to respond") # type: ignore
    ):
        view = TimezoneView()
        await interaction.response.send_message("Pick timezone:", view=view, ephemeral=True)

        await view.wait()

        if not view.timezone:
            return await interaction.followup.send(
                f"Invalid time: {t} ❗ Use format like `3:00 PM`",
                ephemeral=True
            )

        times_list = []
        for t in times.split(","):
            try:
                parsed = parse_time_flexible(t)
                times_list.append(parsed)
            except Exception as e:
                await interaction.followup.send(f"Invalid time: {t} ❗ Use formats like `3:00 PM` or `15:00`", ephemeral=True)
                return

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute("""
        INSERT INTO reminders (
            guild_id, channel_id, creator_id, target_id,
            message, times, timezone, one_time,
            reward_points, response_time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            interaction.guild.id,
            interaction.channel.id,
            interaction.user.id,
            user.id,
            message,
            json.dumps(times_list),
            view.timezone,
            int(one_time),
            reward_points,
            response_time or 600
        ))

        conn.commit()
        conn.close()

        # ✅ EMBED RESPONSE
        embed = discord.Embed(
            title="✅ Reminder Created",
            description=f"Reminder set for {user.mention}",
            color=discord.Color.green()
        )

        embed.add_field(name="Message", value=message, inline=False)
        embed.add_field(name="Times", value=times, inline=False)
        embed.add_field(name="Timezone", value=view.timezone, inline=True)
        embed.add_field(name="Type", value="One-Time" if one_time else "Recurring", inline=True)

        await interaction.followup.send(embed=embed)

     # ------------------ STATS ------------------ #
    @discord.slash_command(name="reminder_stats", description="Check reminder stats", guild_ids=GUILD_IDS)
    async def reminder_stats(self, interaction, user: discord.Member):

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute("SELECT points FROM user_points WHERE user_id = ?", (user.id,))
        points = c.fetchone()
        points = points[0] if points else 0

        c.execute("SELECT SUM(missed_count) FROM reminders WHERE target_id = ?", (user.id,))
        missed = c.fetchone()[0] or 0

        conn.close()

        await interaction.response.send_message(
            f"{user.mention}\n💰 Points: {points}\n❌ Missed: {missed}"
        )

    # CANCEL REMINDER
    @discord.slash_command(name="cancel_reminder", description="Cancel a reminder", guild_ids=GUILD_IDS)
    async def cancel_reminder(
        self,
        interaction: discord.ApplicationContext,
        reminder_id: discord.Option(int, "Reminder ID") # type: ignore
    ):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        conn.commit()
        conn.close()

        await interaction.response.send_message("Reminder cancelled ✔️", ephemeral=True)

    # EDIT REMINDER
    @discord.slash_command(name="edit_reminder", description="Edit reminder", guild_ids=GUILD_IDS)
    async def edit_reminder(
        self,
        interaction: discord.ApplicationContext, # type: ignore
        reminder_id: discord.Option(int), # type: ignore
        new_message: discord.Option(str, required=False), # type: ignore
        new_times: discord.Option(str, required=False), # type: ignore
        new_channel: discord.Option(discord.TextChannel, required=False) # type: ignore
    ):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        if new_message:
            c.execute("UPDATE reminders SET message = ? WHERE id = ?", (new_message, reminder_id))

        if new_times:
            times_list = [t.strip() for t in new_times.split(",")]
            c.execute("UPDATE reminders SET times = ? WHERE id = ?", (json.dumps(times_list), reminder_id))

        if new_channel:
            c.execute("UPDATE reminders SET channel_id = ? WHERE id = ?", (new_channel.id, reminder_id))

        conn.commit()
        conn.close()

        await interaction.response.send_message("Reminder updated ✔️", ephemeral=True)

    # LIST REMINDERS
    @discord.slash_command(name="list_reminders", description="List reminders", guild_ids=GUILD_IDS)
    async def list_reminders(self, interaction: discord.ApplicationContext):

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute("SELECT id, message, times, timezone FROM reminders")
        data = c.fetchall()

        conn.close()

        if not data:
            return await interaction.response.send_message("No reminders found", ephemeral=True)

        embed = discord.Embed(
            title="📋 Active Reminders",
            color=discord.Color.blurple()
        )

        for r in data:
            rid, msg, times_json, tz = r
            times_list = json.loads(times_json)

            # Convert back to 12h display
            pretty_times = []
            for t in times_list:
                dt = datetime.strptime(t, "%H:%M")
                pretty_times.append(dt.strftime("%I:%M %p"))

            embed.add_field(
                name=f"ID {rid}",
                value=f"{msg}\n🕒 {', '.join(pretty_times)}\n🌍 {tz}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.slash_command(name="test_reminder", description="Test reminder system", guild_ids=GUILD_IDS)
    @commands.has_permissions(administrator=True)
    async def test_reminder(
        self,
        interaction: discord.ApplicationContext, # type: ignore
        user: discord.Option(discord.Member)  # type: ignore
    ):
        view = ReminderView(
            reminder_id=0,
            creator_id=interaction.user.id,
            target_id=user.id
        )

        await interaction.response.send_message(
            f"{user.mention} Test reminder!",
            view=view
        )


def setup(client):
    client.add_cog(Reminder(client))