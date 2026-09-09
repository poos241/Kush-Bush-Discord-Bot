class VerificationWorker {

    start() {

        setInterval(async () => {

            await this.processPendingFriends();

            await this.processPendingGroups();

            await this.processRoleSync();

        }, 30000);

    }

    async processPendingFriends() {

    }

    async processPendingGroups() {

    }

    async processRoleSync() {

    }

}

export default new VerificationWorker();