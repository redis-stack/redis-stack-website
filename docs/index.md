# How to add a multi-language code example to redis.io

## Introduction

The [redis.io](https://redis.io) website gets built from multiple source code repositories (e.g., the core Redis documentation or the modules documentation). Going forward, we will call such a content source a ‘component’. The actual code examples will be pulled from an external repository, but most of the configuration changes are performed in the repository ‘redis-stack-website’, which glues it all together.

## Configure Hugo

The website redis.io is built from Markdown files via Hugo. Hugo is “one of the most popular open-source static site generators”. 

Hugo can be configured via a configuration file that is called `config.toml`. The section `[params]` contains a parameter clientExamples. The currently configured value is the following one:

```toml
clientsExamples = ["C#", "Go", "Java", "Node.js", "Python"]
```

Any new programming language needs to be added to this list. The order of the items in this list does matter. C# will appear first, followed by Go, Java, Node, and Python. **Please keep it consistent with the order on page https://redis.io/docs/clients/.**

This configuration, along with the configuration of the steps below, is used to control the behavior of the Hugo shortcode that was developed to show tabbed code examples. A shortcode is a simple snippet inside a content file that Hugo will render using a predefined template. This template can contain HTML and JavaScript.

### How to add a new programming language

> You can skip the instructions for this step if your client library is already registered.

The folder `data/stack` contains several component configuration files. We decided that most of our code examples should be located within the language-specific client library repository, so we are interested in adding a configuration for a client library component.

Here is the example configuration file `jedis.json`: 

```json
{
  "id": "jedis",
  "type": "client",
  "name": "jedis",
  "language": "Java",
  "repository": {
      "git_uri": "https://github.com/redis/jedis"
  },
  "examples": {
      "git_uri": "https://github.com/redis/jedis",
      "dev_branch": "master",
      "path": "src/test/java/redis/clients/jedis/doc",
      "pattern": "*.java"
  }
}
```

The language property needs to match the value that was added to the `config.toml` file in the previous step. The `examples` property points to a Git repository, a branch, a path under which examples should be searched, and a file name pattern. The current logic will scan for examples that fulfill the filename pattern within the given path.

> The `examples` property does currently not support a collection of configuration values. If you need to add multiple source folders of a client library (e.g., doc/examples and tests/doc), you could add multiple such configuration files.


Finally, you must ensure that your component is registered by adding it to the `index.json` file inside the same folder. The entry should match the file name prefix and ID of the component.

Here is an example:
```json
…
"clients": [
        "go_redis",
        "node_redis",
        "redis_py",
        "redis_py_test",
        "jedis"
    ],
…
```

### Verify that your language is supported by the source code file parser

> You could skip the instructions of this step if your programming language was already added to the parser.


As seen in the previous step, a client component contains an example definition. The component handling is implemented in `build/stack/component.py`. The example file parser that is used by it is implemented inside `build/stack/example.py`. You might want to extend the parser to support your language better. Right now the following language-specific settings are baked into the source code:

```python
TEST_MARKER = {
    'java': '@Test',
    'c#': '\[Fact\]'
}
PREFIXES = {
    'python': '#',
    'javascript': '//',
    'java': '//',
    'go': '//',
    'c#': '//',
}
```

The `TEST_MARKER` dictionary maps programming languages to test framework annotations, which allows the parser to filter such source code lines out. The `PREFIXES` dictionary maps the language to the comment prefix that is used by it. Python, for instance, uses a hashtag (#) to start a comment.

> Especially commands-specific code examples should be executed as part of the standard test suite of the client library. This will ensure that we can keep the documentation up to date when the signature of a command-related function/method changes within the client library. The idea is that the client library maintainers inform the documentation team when such a test fails.


## Add your example to the client library

Please perform the following steps to add your source code example:

1. Add a source code file under a client-specific subfolder as specified in the table below:

| Programming Language | GitHub Repo                                         |
|----------------------|-----------------------------------------------------|
| C#                   | [NRedisStack](https://github.com/redis/NRedisStack) |
| Go                   | [go-redis](https://github.com/redis/go-redis)       |
| Java                 | [jedis](https://github.com/redis/jedis)             |
| Node.js              | [node-redis](https://github.com/redis/node-redis)   |
| Python               | [redis-py](https://github.com/redis/redis-py)       |

2. Define an example ID with the help of a comment in the first line of the example code file the following way: `EXAMPLE: myid`

> **Important:** Examples are grouped together based on their ID. This means a Python example with the same id as a C# example will appear under the same tab group on redis.io.

You can find an example of a code example file in each client specified above.

### Understand special comments in the example source code files

The code example use some special comments, such as `HIDE_START` or `REMOVE_START`. The following list gives an explanation:

- `EXAMPLE`: Defines the identifier of the source code example file, whereby `$id` is any common string (e.g., `set_and_get`). Such a string should not contain white spaces or other fancy characters. We recommend limiting it to alphanumeric characters, underline (`_`), or hyphen (`-`).
- `HIDE_START`: Starts a code block that should be ‘by default hidden’ when showing the example. This code block will only become visible if the ‘Unhide’ button is clicked.
- `HIDE_END`: End a ‘by default hidden’ code block
- `REMOVE_START`: Starts a code block that should be entirely removed when taking the example over. This is in particular useful to remove lines of code that do not contribute to the example but are needed to embed the code into a proper test case. Good examples of such code blocks are imports of external libraries or test assertions.
- `REMOVE_END`: End of a code block that should be removed from the example
- `STEP_START $stepName`: Starts a code block that can be referenced as a step in a step-by-step guide. See step 6 for short code usage examples. 
- `STEP_END`: End of a code block that can be referenced as a step in step-by-step guides.

## Add your example to the content page

In order to add a multi-language code example to a content page, the following Hugo shortcode needs to be added:

```
{{< clients-example $id />}}
```

The ID is the same one as specified with `EXAMPLE: $id` in the first line of your code example.

When converting existing content with redis-cli examples to the new format, you can wrap the existing redis-cli example:

```
{{< clients-example set_and_get >}}
> set mykey somevalue
OK
> get mykey
"somevalue"
{{< /clients-example >}}
```

If redis-cli example is too long you can hide some lines by specifying the limit as the fourth argument:

```
{{< clients-example set_and_get "" "" 2 >}}
> set mykey somevalue
OK
> get mykey <-- this line will be hidden
"somevalue" <-- this line will be hidden
{{< /clients-example >}}
```

In  order to refer to a particular step placed in between `STEP_START $stepName` and `STEP_END` comments in the code example, you should use the second argument to define the name of the step:

```
{{< clients-example $id $stepName />}}
```

If you need to embed an example for a specific programming language, the third argument should be defined:
```
{{< clients-example $id $stepName $lang />}}
```
The following example shows the `connect` step of the Python example:
```
{{< clients-example set_and_get connect Python />}}
```
The programming language name should match with configuration explained in the "Configure Hugo" section.

Given that redis.io is built from several sources, the modification needs to happen in the actual source content. The command documentation of Redis core commands can be found here:

https://github.com/redis/redis-doc

The modules-specific documentation does currently live within the module source code repositories. The documentation of the RediSearch commands, for instance, is located here:

https://github.com/RediSearch/RediSearch/tree/master/docs

### Test your example locally

You can test your example locally without modifying the actual source content the following way:

1. Check out the adds-client-examples branch out from GitHub
   - Clone this repo
   - Change the directory to the folder redis-stack-website
   - Switch the branch via git checkout adds-client-examples
2. Run `make clean netlify up`
3. Modify a file, e.g., `content/en/commands/get/index.md`
4. Add the Hugo shortcode to the location where you want the example to display
5. Open the browser to `localhost:1313`  and navigate to the page you modified,
