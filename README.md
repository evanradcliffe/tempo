# Developer Module

This is your personal development workspace for the CCC Winter26 project.

## Important Rules & Guidelines

* **Your Workspace:** You have exclusive write access to this directory (and its associated repository). 
* **Other Directories:** Please do not make any changes in your colleagues' directories. These will either be blocked during push or cause conflicts.
* **Global Changes:** If you need changes to central files (outside of this directory), please create a Merge Request in the main project or contact the Maintainer.

## Getting Started

1. Make sure you have cloned the main project using the `--recursive` flag.
2. Write your code exclusively inside this directory.
3. Use central project classes via relative imports (e.g., `import ../../core/config`).


## Publishing Code

When you are done, commit and push your changes as usual **from within this directory**:

```bash
git add my_file.py
git commit -m "feat: Added new feature"
git push origin main
```
_Note: Your changes will only become visible in the main system once the Maintainer updates the submodule pointer in the main repository._


