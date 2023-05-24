import glob
import json
import re
import yaml
import tabulate


content_path = 'content/en/**/*.md'
examples_json_path = 'data/examples.json'

shortcode_pattern = r'{{[%,<]\s*clients\-example\s*"?\s*([\w|\-]+)\s*"?\s*"?\s*([\w|\-]*)\s*"?.*/*[%,>]}}'


class Example:
    def __init__(self, example_id, implementations=None):
        self.example_id = example_id
        self.used_in = {}
        self.steps = {}
        self.implementations = implementations

    def add_reference(self, path, github_src=None, step=None):
        self.used_in[path] = github_src

        if step is None:
            if step not in self.steps:
                self.steps[step] = []
            self.steps[step].append((path, github_src))

    def to_markdown(self):
        markdown = f"## Example ID: {self.example_id}\n"
        markdown += f"### Available implementations and steps:\n"

        if self.implementations is not None:

            all_steps = set()
            for i in self.implementations.values():
                all_steps.update(i['named_steps'].keys())

            all_steps = list(sorted(all_steps))

            table = []
            headers = ["Language"]

            if len(all_steps) > 0:
                headers += all_steps

            for lang, impl in self.implementations.items():
                row = [f" [{lang}]({impl['sourceUrl']}) "]

                if not all_steps:
                    table.append(row)
                    continue

                if not impl['named_steps']:
                    row += ["-"] * len(all_steps)
                    table.append(row)
                    continue

                for step in all_steps:
                    if step in impl['named_steps']:
                        row.append(" + ")
                    else:
                        row.append(" - ")

                table.append(row)

            markdown += tabulate.tabulate(table, tablefmt="github", headers=headers)
            markdown += "\n\n"

        markdown += f"### Used in:\n"
        for path, github_src in self.used_in.items():
            markdown += f"- [{path}]({github_src})\n"
        markdown += "\n"

        if self.steps:
            markdown += f"### Steps used in:\n"
            for step, files in self.steps.items():
                markdown += f"#### Step: {step}\n"
                for path, github_src in files:
                    markdown += f"- [{path}]({github_src})\n"
                markdown += "\n"

        return markdown


referenced_examples = {}


with open(examples_json_path, 'r') as f:
    example_implementations = json.load(f)

    for example_id, example_impl in example_implementations.items():
        referenced_examples[example_id] = Example(example_id, implementations=example_impl)


for file in glob.glob(content_path, recursive=True):
    with open(file, 'r') as f:
        contents = f.read()

        # Parse YAML metadata
        github_src_path = None

        yaml_header = re.search(r'---\n(.*?)---\n', contents, re.DOTALL)
        if yaml_header:
            metadata = yaml.safe_load(yaml_header.group(1))

            try:
                github_src_path = (
                    f"{metadata['github_repo']}/tree/{metadata['github_branch']}/{metadata['github_path']}"
                )
            except KeyError:
                pass

        # Extract all clients-example short codes
        matches = re.findall(shortcode_pattern, contents, re.MULTILINE)
        for match in matches:
            example_id, step_id = match
            if example_id not in referenced_examples:
                referenced_examples[example_id] = Example(example_id)
            referenced_examples[example_id].add_reference(
                file, github_src=github_src_path, step=step_id
            )


with open('./docs/examples.md', 'w') as summary:
    summary.write("# Redis.io Code Examples Index\n")
    for _, example in referenced_examples.items():
        summary.write(example.to_markdown())
