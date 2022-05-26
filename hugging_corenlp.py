"""
This script allows for pushing of the corenlp models to N different huggingface repos.

Generously provided by Omar Sanseviero

huggingface-cli login
python3 hugging_corenlp.py --input_dir <models_path>  --branch <version>
"""

import argparse
import datetime
import os
import shutil

from collections import namedtuple

from huggingface_hub import  Repository, HfApi, HfFolder

def get_model_card(lang):
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    model_card = """---
tags:
- corenlp
library_tag: corenlp
language:
- {lang}
license: gpl-2.0
---
# Core NLP model for {lang}
CoreNLP is your one stop shop for natural language processing in Java! CoreNLP enables users to derive linguistic annotations for text, including token and sentence boundaries, parts of speech, named entities, numeric and time values, dependency and constituency parses, coreference, sentiment, quote attributions, and relations.
Find more about it in [our website](https://stanfordnlp.github.io/CoreNLP) and our [GitHub repository](https://github.com/stanfordnlp/CoreNLP).

This card and repo were automatically prepared with `hugging_corenlp.py` in the `stanfordnlp/huggingface-models` repo

Last updated {now}
""".format(lang=lang, now=now)
    return model_card

# local_name is a potential alternate name for the file
# remote_name is the name to use when pushing remotely
# repo_name is the repo name if corenlp-model is not suitable for some reason
Model = namedtuple("Model", 'model_name, local_name, remote_name, repo_name')

MODELS = [
    Model("CoreNLP",          "stanford-corenlp-latest.zip",                     "stanford-corenlp-latest.zip", "CoreNLP"),
    Model("arabic",           "stanford-arabic-corenlp-models-current.jar",      None,                          None),
    Model("chinese",          "stanford-chinese-corenlp-models-current.jar",     None,                          None),
    Model("english-default",  "stanford-corenlp-models-current.jar",             None,                          None),
    Model("english-extra",    "stanford-english-corenlp-models-current.jar",     None,                          None),
    Model("english-kbp",      "stanford-english-kbp-corenlp-models-current.jar", None,                          None),
    Model("french",           "stanford-french-corenlp-models-current.jar",      None,                          None),
    Model("german",           "stanford-german-corenlp-models-current.jar",      None,                          None),
    Model("hungarian",        "stanford-hungarian-corenlp-models-current.jar",   None,                          None),
    Model("italian",          "stanford-italian-corenlp-models-current.jar",     None,                          None),
    Model("spanish",          "stanford-spanish-corenlp-models-current.jar",     None,                          None),
]

def write_model_card(repo_local_path, model):
    """
    Write a README for the current model to the given path
    """
    readme_path = os.path.join(repo_local_path, "README.md")
    with open(readme_path, "w") as f:
        f.write(get_model_card(model))

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', type=str, default="/home/john/extern_data/corenlp/", help='Directory for loading the CoreNLP models')
    parser.add_argument('--version', type=str, default="4.4.0", help='Version of corenlp models to upload')
    args = parser.parse_args()
    return args


def push_to_hub():
    args = parse_args()
    input_dir = args.input_dir

    api = HfApi()

    for model in MODELS:
        # Create the repository
        model_name = model.model_name
        repo_name = model.repo_name if model.repo_name else "corenlp-%s" % model_name
        repo_url = api.create_repo(
            name=repo_name,
            token=HfFolder.get_token(),
            organization="stanfordnlp",
            exist_ok=True,
        )

        # Clone the repository
        repo_local_path = os.path.join("hub", repo_name)

        repo = Repository(repo_local_path, clone_from=repo_url)
        # checkout "main" so that we know we are tracking files correctly
        repo.git_checkout("main")
        repo.git_pull(rebase=True)

        # Make sure jar files are tracked with LFS
        repo.lfs_track(["*.jar"])
        repo.lfs_track(["*.zip"])
        repo.push_to_hub(commit_message="Update tracked files", clean_ok=True)

        # Create a copy of the jar file in the repository
        src = f"stanford-corenlp-models-{model_name}.jar"
        dst = model.remote_name if model.remote_name else os.path.join(repo_local_path, src)
        if input_dir:
            src = os.path.join(input_dir, src)
        if not os.path.exists(src):
            if input_dir:
                new_src = os.path.join(input_dir, model.local_name)
            else:
                new_src = model.local_name
            if not os.path.exists(new_src):
                raise FileNotFoundError(f"Cannot find {model_name} model.  Looked for {src} and {new_src}")
            src = new_src
        shutil.copy(src, dst)

        # Create the model card
        write_model_card(repo_local_path, model_name)

        # Push the model
        # note: the error of not having anything to push will hopefully
        # never happen since the README is updated to the millisecond
        print("Pushing files to the Hub")
        repo.push_to_hub(commit_message=f"Add model for version {args.version}")

        tag = "v" + args.version
        if repo.tag_exists(tag):
            repo.delete_tag(tag, remote="origin")
        repo.add_tag(tag_name=tag, message=f"Adding new version of models {tag}", remote="origin")
        print(f"Added a tag for the new models: {tag}")

        print(f"View your model in {repo_url}")


if __name__ == '__main__':
    push_to_hub()
