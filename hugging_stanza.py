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
- corenlp
library_tag: corenlp
language:
- {lang}
license: GNU
---
# Core NLP model for {lang}
CoreNLP is your one stop shop for natural language processing in Java! CoreNLP enables users to derive linguistic annotations for text, including token and sentence boundaries, parts of speech, named entities, numeric and time values, dependency and constituency parses, coreference, sentiment, quote attributions, and relations.
Find more about it in [our website](https://stanfordnlp.github.io/CoreNLP) and our [GitHub repository](https://github.com/stanfordnlp/CoreNLP).

Last updated {now}
""".format(lang=lang, now=now)
    return model_card

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
        repo.git_pull(rebase=True)

        # Make sure jar files are tracked with LFS
        repo.lfs_track(["*.zip"])
        repo.lfs_track(["*.pt"])
        try:
            repo.push_to_hub(commit_message="Update tracked files")
        except EnvironmentError as e:
            # tree clean or directory clean depending on version
            if "nothing to commit, working" in str(e):
                print(f"{repo_url} is already tracking .zip and .pt files")
            else:
                raise

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
        repo.push_to_hub(commit_message="Add model")

        branch = "v" + args.version
        repo.git_checkout(branch, create_branch_ok=True)
        try:
            repo.git_pull(rebase=True)
        except OSError as e:
            if "There is no tracking information for the current branch" in str(e):
                print(f"{repo_url} does not yet have branch {branch}")
            else:
                raise

        write_model_card(repo_local_path, model)
        copytree(src, dst)
        repo.push_to_hub(commit_message="Add models")

        print(f"View your model in {repo_url}")

if __name__ == '__main__':
    push_to_hub()
