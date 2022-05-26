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

def get_model_card(lang, model):
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    model_card = """---
tags:
- corenlp
library_tag: corenlp
language: {lang}
license: gpl-2.0
---
# Core NLP model for {model}
CoreNLP is your one stop shop for natural language processing in Java! CoreNLP enables users to derive linguistic annotations for text, including token and sentence boundaries, parts of speech, named entities, numeric and time values, dependency and constituency parses, coreference, sentiment, quote attributions, and relations.
Find more about it in [our website](https://stanfordnlp.github.io/CoreNLP) and our [GitHub repository](https://github.com/stanfordnlp/CoreNLP).

This card and repo were automatically prepared with `hugging_corenlp.py` in the `stanfordnlp/huggingface-models` repo

Last updated {now}
""".format(lang=lang, model=model, now=now)
    return model_card

# lang is an abbrev to use in the model card
# local_name is a potential alternate name for the file
# remote_name is the name to use when pushing remotely
# repo_name is the repo name if corenlp-model is not suitable for some reason
Model = namedtuple("Model", 'model_name, lang, local_name, remote_name, repo_name')

MODELS = [
    Model("CoreNLP",          "en",   "stanford-corenlp-latest.zip",                     "stanford-corenlp-latest.zip", "CoreNLP"),
    Model("arabic",           "ar",   "stanford-arabic-corenlp-models-current.jar",      None,                          None),
    Model("chinese",          "zh",   "stanford-chinese-corenlp-models-current.jar",     None,                          None),
    Model("english-default",  "en",   "stanford-corenlp-models-current.jar",             None,                          None),
    Model("english-extra",    "en",   "stanford-english-corenlp-models-current.jar",     None,                          None),
    Model("english-kbp",      "en",   "stanford-english-kbp-corenlp-models-current.jar", None,                          None),
    Model("french",           "fr",   "stanford-french-corenlp-models-current.jar",      None,                          None),
    Model("german",           "de",   "stanford-german-corenlp-models-current.jar",      None,                          None),
    Model("hungarian",        "hu",   "stanford-hungarian-corenlp-models-current.jar",   None,                          None),
    Model("italian",          "it",   "stanford-italian-corenlp-models-current.jar",     None,                          None),
    Model("spanish",          "es",   "stanford-spanish-corenlp-models-current.jar",     None,                          None),
]

def write_model_card(repo_local_path, lang, model):
    """
    Write a README for the current model to the given path
    """
    readme_path = os.path.join(repo_local_path, "README.md")
    with open(readme_path, "w") as f:
        f.write(get_model_card(lang, model))

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', type=str, default="/home/john/extern_data/corenlp/", help='Directory for loading the CoreNLP models')
    parser.add_argument('--output_dir', type=str, default="/home/john/huggingface/hub", help='Directory with the repos')
    parser.add_argument('--version', type=str, default="4.4.0", help='Version of corenlp models to upload')
    args = parser.parse_args()
    return args


def push_to_hub():
    args = parse_args()
    input_dir = args.input_dir

    api = HfApi()

    for model in MODELS:
        # Create the repository
        lang = model.lang
        model_name = model.model_name
        repo_name = model.repo_name if model.repo_name else "corenlp-%s" % model_name
        repo_url = api.create_repo(
            name=repo_name,
            token=HfFolder.get_token(),
            organization="stanfordnlp",
            exist_ok=True,
        )

        # Clone the repository
        repo_local_path = os.path.join(args.output_dir, repo_name)

        repo = Repository(repo_local_path, clone_from=repo_url)
        # checkout "main" so that we know we are tracking files correctly
        repo.git_checkout("main")
        repo.git_pull(rebase=True)

        # Make sure jar files are tracked with LFS
        repo.lfs_track(["*.jar"])
        repo.lfs_track(["*.zip"])
        repo.push_to_hub(commit_message="Update tracked files", clean_ok=True)

        # Create a copy of the jar file in the repository
        dst = model.remote_name if model.remote_name else os.path.join(repo_local_path, src)
        src_candidates = [f"stanford-corenlp-models-{model_name}.jar",
                          model.local_name,
                          # stanford-corenlp-4.4.0-models-arabic.jar
                          f"stanford-corenlp-{args.version}-models-{model_name}.jar"]
        for src in src_candidates:
            if input_dir:
                src = os.path.join(input_dir, src)
            if os.path.exists(src):
                break
        else:
            if input_dir:
                locations_searched = ", ".join(os.path.join(input_dir, src) for src in src_candidates)
            else:
                locations_searched = ", ".join(src_candidates)
            raise FileNotFoundError(f"Cannot find {model_name} model.  Looked in {locations_searched}")
        shutil.copy(src, dst)

        # Create the model card
        write_model_card(repo_local_path, lang, model_name)

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
