"""
This script allows for pushing of the corenlp models to N different huggingface repos.

Generously provided by Omar Sanseviero

huggingface-cli login
python hugging_stanza.py --input_dir <models_path>  --version <version>
"""

import argparse
import datetime
import os
import shutil
from pathlib import Path

from stanza.resources.common import list_available_languages
from stanza.models.common.constant import lcode2lang, lang2lcode

from huggingface_hub import HfApi

def get_model_card(lang):
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    full_lang = lcode2lang.get(lang, None)
    short_lang = lang2lcode.get(lang, lang)
    short_lang = short_lang.split("-")[0]
    lang_text = f"{full_lang} ({lang})" if full_lang else lang
    model_card = """---
tags:
- stanza
- token-classification
library_name: stanza
language: {short_lang}
license: apache-2.0
---
# Stanza model for {lang_text}
Stanza is a collection of accurate and efficient tools for the linguistic analysis of many human languages. Starting from raw text to syntactic analysis and entity recognition, Stanza brings state-of-the-art NLP models to languages of your choosing.
Find more about it in [our website](https://stanfordnlp.github.io/stanza) and our [GitHub repository](https://github.com/stanfordnlp/stanza).

This card and repo were automatically prepared with `hugging_stanza.py` in the `stanfordnlp/huggingface-models` repo

Last updated {now}
""".format(short_lang=short_lang, lang_text=lang_text, now=now)
    return model_card

def parse_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--input_dir', type=str, default="/u/nlp/software/stanza/models/", help='Directory for loading the stanza models.  Will first try input_dir + version, if that exists')
    parser.add_argument('--version', type=str, default="1.5.1", help='Version of stanza models to upload')
    parser.add_argument('lang', nargs='*', help='List of languages.  Will default to all languages')
    args = parser.parse_args()
    if len(args.lang) == 0:
        # TODO: use version to get the available languages
        # TODO: skip languages where the version and the data didn't change
        args.lang = list_available_languages()
    return args

def push_to_hub():
    args = parse_args()
    input_dir = args.input_dir
    if os.path.exists(input_dir + args.version):
        input_dir = input_dir + args.version
        print("Found directory in %s - using that instead of %s" % (input_dir, args.input_dir))

    new_tag_name = "v" + args.version

    api = HfApi()

    print("Processing languages: {}".format(args.lang))
    for model in args.lang:
        print(f"Processing {model}")
        # Create the repository
        repo_name = "stanza-" + model
        repo_id = "stanfordnlp/" + repo_name
        repo_url = api.create_repo(
            repo_id=repo_id,
            exist_ok=True
        )

        # Find src folder
        src = Path(input_dir) / model
        if not src.exists():
            if not input_dir:
                raise FileNotFoundError(f"Could not find models under {src}.  Perhaps you forgot to set --input_dir?")
            else:
                raise FileNotFoundError(f"Could not find models under {src}")

        # Update model card in it
        (src / "README.md").write_text(get_model_card(model))

        # Upload model + model card
        # setting delete_patterns will clean up old model files as we go
        api.upload_folder(repo_id=repo_id, folder_path=src, commit_message=f"Add model {args.version}", delete_patterns="*.pt")

        # Check and delete tag if already exist
        refs = api.list_repo_refs(repo_id=repo_id)
        for tag in refs.tags:
            if tag.name == new_tag_name:
                api.delete_tag(repo_id=repo_id, tag=new_tag_name)
                break

        # Tag model version
        api.create_tag(repo_id=repo_id, tag=new_tag_name, tag_message=f"Adding new version of models {new_tag_name}")
        print(f"Added a tag for the new models: {new_tag_name}")
        print(f"View your model in:\n  {repo_url}\n\n")

if __name__ == '__main__':
    push_to_hub()
