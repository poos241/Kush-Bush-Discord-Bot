type CacheEntry<T> = {
    value: T;
    expires: number;
};

class UserCache {

    private cache = new Map<string, CacheEntry<any>>();

    get(key: string) {

        const item = this.cache.get(key);

        if (!item)
            return null;

        if (Date.now() > item.expires) {

            this.cache.delete(key);

            return null;

        }

        return item.value;

    }

    set(key: string, value: any, seconds = 60) {

        this.cache.set(key, {

            value,

            expires: Date.now() + (seconds * 1000)

        });

    }

    clear() {

        this.cache.clear();

    }

}

export default new UserCache();