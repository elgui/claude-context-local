"""Shell completion utilities for csearch CLI."""

import os
import sys
from pathlib import Path

import click


# Completion scripts
BASH_COMPLETION = '''
# csearch bash completion
_csearch_completion() {
    local IFS=$'\\n'
    local response

    response=$(env COMP_WORDS="${COMP_WORDS[*]}" COMP_CWORD=$COMP_CWORD _CSEARCH_COMPLETE=bash_complete $1)

    for completion in $response; do
        IFS=',' read type value <<< "$completion"

        if [[ $type == 'dir' ]]; then
            COMPREPLY=()
            compopt -o dirnames
        elif [[ $type == 'file' ]]; then
            COMPREPLY=()
            compopt -o default
        elif [[ $type == 'plain' ]]; then
            COMPREPLY+=($value)
        fi
    done

    return 0
}

_csearch_completion_setup() {
    complete -o nosort -F _csearch_completion csearch
}

_csearch_completion_setup;
'''

ZSH_COMPLETION = '''#compdef csearch

_csearch() {
    local -a completions
    local -a completions_with_descriptions
    local -a response
    (( ! $+commands[csearch] )) && return 1

    response=("${(@f)$(env COMP_WORDS="${words[*]}" COMP_CWORD=$((CURRENT-1)) _CSEARCH_COMPLETE=zsh_complete csearch)}")

    for key descr in ${(kv)response}; do
        if [[ "$descr" == "_" ]]; then
            completions+=("$key")
        else
            completions_with_descriptions+=("$key":"$descr")
        fi
    done

    if [ -n "$completions_with_descriptions" ]; then
        _describe -V unsorted completions_with_descriptions -U
    fi

    if [ -n "$completions" ]; then
        compadd -U -V unsorted -a completions
    fi
}

compdef _csearch csearch;
'''

FISH_COMPLETION = '''# csearch fish completion

function __fish_csearch_complete
    set -l response (env _CSEARCH_COMPLETE=fish_complete COMP_WORDS=(commandline -cp) COMP_CWORD=(commandline -t) csearch)

    for completion in $response
        set -l metadata (string split "," -- $completion)

        if [ $metadata[1] = "dir" ]
            __fish_complete_directories $metadata[2]
        else if [ $metadata[1] = "file" ]
            __fish_complete_path $metadata[2]
        else if [ $metadata[1] = "plain" ]
            echo $metadata[2]
        end
    end
end

complete --no-files --command csearch --arguments "(__fish_csearch_complete)"
'''


def get_completion_script(shell: str) -> str:
    """Get completion script for the specified shell.

    Args:
        shell: Shell type (bash, zsh, or fish).

    Returns:
        Completion script content.
    """
    scripts = {
        "bash": BASH_COMPLETION,
        "zsh": ZSH_COMPLETION,
        "fish": FISH_COMPLETION,
    }
    return scripts.get(shell, "")


def get_completion_install_path(shell: str) -> Path:
    """Get the default installation path for completions.

    Args:
        shell: Shell type.

    Returns:
        Path where completion script should be installed.
    """
    home = Path.home()

    paths = {
        "bash": home / ".bash_completion.d" / "csearch",
        "zsh": home / ".zfunc" / "_csearch",
        "fish": home / ".config" / "fish" / "completions" / "csearch.fish",
    }
    return paths.get(shell, Path("/dev/null"))


def install_completion(shell: str, output_path: Path = None) -> bool:
    """Install completion script for the specified shell.

    Args:
        shell: Shell type.
        output_path: Custom output path (optional).

    Returns:
        True if installed successfully.
    """
    script = get_completion_script(shell)
    if not script:
        return False

    path = output_path or get_completion_install_path(shell)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script)

    return True


def detect_shell() -> str:
    """Detect the current shell.

    Returns:
        Shell name (bash, zsh, or fish).
    """
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        return "zsh"
    elif "fish" in shell:
        return "fish"
    else:
        return "bash"


# Click completion registration
def register_completions():
    """Register completion values for Click commands."""
    pass  # Click handles this automatically with its built-in completion support
