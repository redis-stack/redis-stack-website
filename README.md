## Documentation

OPEN SOURCE LICENSE VS. TRADEMARKS. The three-clause BSD license gives you the right to redistribute and use the software in source and binary forms, with or without modification, under certain conditions. However, open source licenses like the three-clause BSD license do not address trademarks. For further details please read the [Redis Trademark Policy](https://www.redis.com/legal/trademark-policy)."

- [How to add a multi-language code example to redis.io](https://redis-stack.github.io/redis-stack-website/)
- [Code examples index](https://redis-stack.github.io/redis-stack-website/examples/)

## Prereqs
`pip install -r requirements.txt`
`npm install`
`brew install hugo`
`make netlify`
`make up`

---

After cloning `redis-stack-website`, run `make docker` to build and run a container that serves hugo on `localhost:1313` with the components defined in `redis_stack_components.yml`.

The site is generated inside the container.

In order to invoke a short-loop of changes, it's possible to `make docker-sh VOL=/home/repos` (replace `/home/repos` with your repo directory), which will run the container (assuming you've already generated it).

At this point it is possible to modify `redis_stack_components.yml` within the container with location of repos  (e.g. `git_path: /home/repos/RedisJSON`) - do not forget to remark-out `git_url`.

At this stage, from within the container run `make build`.

This will generate the site based on your local repo changes.

`make up` will bring up hugo so it is possible to examine the site from your host's browser.

---

