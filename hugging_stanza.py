"""
This script allows for pushing of the corenlp models to N different huggingface repos.

Generously provided by Omar Sanseviero

huggingface-cli login
python hugging_corenlp.py --input_dir <models_path>  --branch <version>
"""

import argparse
import datetime
import os
import shutil

from stanza.resources.common import list_available_languages

from huggingface_hub import  Repository, HfApi, HfFolder

def get_model_card(lang):
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    model_card = """---
tags:
- stanza
library_tag: stanza
language:
- {lang}
license: GNU
---
# Stanza model for {lang}
Stanza is a collection of accurate and efficient tools for the linguistic analysis of many human languages. Starting from raw text to syntactic analysis and entity recognition, Stanza brings state-of-the-art NLP models to languages of your choosing.
Find more about it in [our website](https://stanfordnlp.github.io/stanza) and our [GitHub repository](https://github.com/stanfordnlp/stanza).

Last updated {now}
""".format(lang=lang, now=now)
    return model_card

# TODO: use version to get the available languages
MODELS = list_available_languages()

def write_model_card(repo_local_path, model):
    """
    Write a README for the current model to the given path
    """
    readme_path = os.path.join(repo_local_path, "README.md")
    with open(readme_path, "w") as f:
        f.write(get_model_card(model))

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', type=str, default="/u/nlp/software/stanza/1.3.0", help='Directory for loading the stanza models')
    parser.add_argument('--version', type=str, default="1.3.0", help='Version of stanza models to upload')
    args = parser.parse_args()
    return args

def copytree(src, dst):
    if os.path.exists(dst):
        print(f"Cleaning up existing {dst}")
        shutil.rmtree(dst)
    # copy all of the models for this subdir
    print(f"Copying models from {src} to {dst}")
    shutil.copytree(src, dst)


def push_to_hub():
    args = parse_args()
    input_dir = args.input_dir

    api = HfApi()

    for model in MODELS:
        print(f"Processing {model}")
        # Create the repository
        repo_name = "stanza-" + model
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
        if not repo.is_repo_clean():
            print("Repo {repo_local_path} is currently not clean.  Unwilling to proceed...")
            break
        repo.git_pull(rebase=True)

        # Make sure jar files are tracked with LFS
        repo.lfs_track(["*.zip"])
        repo.lfs_track(["*.pt"])
        repo.push_to_hub(commit_message="Update tracked files", clean_ok=True)

        dst = os.path.join(repo_local_path, "models")
        src = os.path.join(input_dir, model)
        if not os.path.exists(src):
            if not input_dir:
                raise FileNotFoundError(f"Could not find models under {src}.  Perhaps you forgot to set --input_dir?")
            else:
                raise FileNotFoundError(f"Could not find models under {src}")
        copytree(src, dst)

        # Create the model card
        write_model_card(repo_local_path, model)

        # Push the model
        # note: the error of not having anything to push will hopefully
        # never happen since the README is updated to the millisecond
        print("Pushing files to the Hub")
        repo.push_to_hub(commit_message="Add model {args.version}")

        tag = "v" + args.version
        if repo.tag_exists(tag):
            repo.delete_tag(tag)
        repo.add_tag(tag_name=tag, message=f"Adding new version of models {tag}")
        print(f"Added a tag for the new models: {tag}")

        print(f"View your model in:\n  {repo_url}\n\n")

if __name__ == '__main__':
    push_to_hub()
