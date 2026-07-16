"""
Git operations for cherry-picking assets between branches
"""
import os
import subprocess
from urllib.parse import urlparse
from typing import List, Tuple, Optional
from .config import GIT_OPERATION_TIMEOUT
from .utils import sanitize_for_log


def run_git_command(
    command: List[str],
    cwd: Optional[str] = None,
    timeout: int = GIT_OPERATION_TIMEOUT,
    logger=None
) -> subprocess.CompletedProcess:
    """
    Execute a git command safely without shell=True

    Args:
        command: List of command arguments
        cwd: Working directory
        timeout: Command timeout in seconds
        logger: Logger instance

    Returns:
        CompletedProcess object

    Raises:
        Exception: If command fails
    """
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )

        if result.returncode != 0:
            safe_cmd = ' '.join(command)
            safe_cmd = sanitize_for_log(safe_cmd)
            error_msg = f"Git command failed: {safe_cmd}\nError: {result.stderr}"
            if logger:
                logger.error(error_msg)
            raise Exception(error_msg)

        return result

    except subprocess.TimeoutExpired as e:
        error_msg = f"Git command timed out after {timeout}s: {' '.join(command)}"
        if logger:
            logger.error(error_msg)
        raise Exception(error_msg) from e


def git_config(input_data: dict, logger) -> Tuple[str, str, str]:
    """
    Configure git and clone repository

    Args:
        input_data: Configuration dictionary
        logger: Logger instance

    Returns:
        Tuple of (git_repo_url_with_auth, repository_domain, repo_directory)

    Raises:
        Exception: If git operations fail
    """
    repository_domain = urlparse(input_data["Git_Repository_URL"]).netloc
    git_repo = input_data["Git_Repository_URL"].replace(
        repository_domain,
        f"{input_data['Git_config_username']}:{input_data['Git_password']}@{repository_domain}"
    )

    os.environ["GIT_PYTHON_REFRESH"] = "quiet"

    run_git_command(
        ['git', 'config', '--global', 'user.email', input_data["Git_config_useremail"]],
        logger=logger
    )
    run_git_command(
        ['git', 'config', '--global', 'user.name', input_data["Git_config_username"]],
        logger=logger
    )

    logger.info("Configured git user.name and user.email")

    safe_url = sanitize_for_log(input_data["Git_Repository_URL"])

    pathname = os.path.splitext(input_data["Git_Repository_URL"])[0]
    repo_name = pathname.split('/')[-1]
    repo_dir = os.path.join(os.getcwd(), repo_name)

    # Check if repository already exists
    if os.path.exists(repo_dir) and os.path.isdir(repo_dir):
        logger.info(f"Repository directory already exists: {repo_dir}")
        logger.info("Skipping clone and using existing repository")
        # Update the existing repository
        try:
            logger.info("Fetching latest changes from remote...")
            run_git_command(['git', '-C', repo_dir, 'fetch', '--all'], logger=logger)
            logger.info("Repository updated successfully")
        except Exception as e:
            logger.warning(f"Failed to fetch updates (continuing anyway): {str(e)}")
    else:
        logger.info(f"Cloning Git Repository: {safe_url}")
        run_git_command(['git', 'clone', git_repo], logger=logger)
        logger.info(f"Repository cloned to: {repo_dir}")

    if not os.path.exists(repo_dir):
        raise Exception(f"Repository directory not found: {repo_dir}")

    return git_repo, repository_domain, repo_dir


def git_operations(
    input_data: dict,
    final_asset_list: List[str],
    git_repo: str,
    repo_dir: str,
    logger
) -> str:
    """
    Perform git checkout and commit operations

    Args:
        input_data: Configuration dictionary
        final_asset_list: List of asset file paths
        git_repo: Git repository URL with authentication
        repo_dir: Repository directory path
        logger: Logger instance

    Returns:
        Target commit hash

    Raises:
        Exception: If git operations fail
    """
    logger.info(f"Working Directory: {repo_dir}")
    logger.info("Pulling changes from cloud branch to local branch")

    logger.info(f"Checkout to Source branch: {input_data['Git_SRC_Branch']}")
    run_git_command(['git', 'checkout', input_data["Git_SRC_Branch"]], cwd=repo_dir, logger=logger)

    logger.info(f"Pulling latest changes from Source branch: {input_data['Git_SRC_Branch']}")
    run_git_command(
        ['git', 'pull', git_repo, input_data["Git_SRC_Branch"]],
        cwd=repo_dir,
        logger=logger
    )

    logger.info(f"Checkout to Target branch: {input_data['Git_TGT_Branch']}")
    run_git_command(['git', 'checkout', input_data["Git_TGT_Branch"]], cwd=repo_dir, logger=logger)

    logger.info(f"Pulling latest changes from Target branch: {input_data['Git_TGT_Branch']}")
    run_git_command(
        ['git', 'pull', git_repo, input_data["Git_TGT_Branch"]],
        cwd=repo_dir,
        logger=logger
    )

    logger.info("Checking out assets from Source to Target branch")
    checked_out_count = 0

    # Note: do NOT pre-check whether the asset's directory already exists in the
    # working tree. In a migration the asset usually does NOT exist on the target
    # branch yet - that's the point. `git checkout <src_branch> -- <path>` pulls
    # the file (and creates its parent directories) from the source branch
    # regardless, so a pre-existence check would wrongly skip every new asset.
    for asset in final_asset_list:
        try:
            run_git_command(
                ['git', 'checkout', input_data["Git_SRC_Branch"], '--', asset],
                cwd=repo_dir,
                logger=logger
            )
            logger.info(f"Checked out: {asset}")
            checked_out_count += 1
        except Exception as e:
            # A path that genuinely doesn't exist on the source branch (e.g. the
            # 'zip' variant when the asset was stored as a different format) will
            # fail here - that's expected; only some format variants exist.
            logger.warning(f"Failed to checkout {asset}: {str(e)}")

    if checked_out_count == 0:
        raise Exception("No assets were successfully checked out")

    logger.info(f"Successfully checked out {checked_out_count}/{len(final_asset_list)} assets")

    result = run_git_command(['git', 'status', '--porcelain'], cwd=repo_dir, logger=logger)

    if not result.stdout.strip():
        logger.warning("No changes to commit")
        result = run_git_command(['git', 'log', '-1', '--pretty=format:%H'], cwd=repo_dir, logger=logger)
        return result.stdout.strip()

    commit_message = f"Migration: {input_data['PostMigration_Tag'][0]}"
    logger.info(f"Committing changes: {commit_message}")

    run_git_command(['git', 'add', '-A'], cwd=repo_dir, logger=logger)
    run_git_command(['git', 'commit', '-m', commit_message], cwd=repo_dir, logger=logger)

    logger.info("Pushing changes to remote repository")
    run_git_command(['git', 'push', git_repo, input_data["Git_TGT_Branch"]], cwd=repo_dir, logger=logger)

    result = run_git_command(['git', 'log', '-1', '--pretty=format:%H'], cwd=repo_dir, logger=logger)
    tgt_commit_hash = result.stdout.strip()

    logger.info(f"Target Commit Hash: {tgt_commit_hash}")

    return tgt_commit_hash


def cherrypick(input_data: dict, final_asset_list: List[str], logger) -> str:
    """
    Main function to cherry-pick assets between branches

    Args:
        input_data: Configuration dictionary
        final_asset_list: List of asset file paths
        logger: Logger instance

    Returns:
        Target commit hash

    Raises:
        Exception: If operations fail
    """
    original_cwd = os.getcwd()
    repo_dir = None

    try:
        git_repo, repository_domain, repo_dir = git_config(input_data, logger)
        tgt_commit_hash = git_operations(input_data, final_asset_list, git_repo, repo_dir, logger)

        input_data['TGT_CommitHash_List'] = tgt_commit_hash
        logger.info(f"Cherry-pick completed successfully. Commit: {tgt_commit_hash}")

        return tgt_commit_hash

    except Exception as e:
        logger.error(f"Cherry-pick operation failed: {str(e)}")
        raise

    finally:
        # Match the working reference: do NOT delete the cloned repo. On Windows,
        # git's read-only pack/commit-graph files make shutil.rmtree fail with
        # 'Access is denied' (WinError 5). The clone is left in place and reused
        # on the next run (git_config fetches into the existing directory).
        os.chdir(original_cwd)
