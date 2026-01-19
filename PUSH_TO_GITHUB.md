# Push to GitHub

Your Kubernetes learning repository is ready! Follow these steps to push it to GitHub.

## Option 1: Create Repository on GitHub Website (Recommended)

### Step 1: Create Repository on GitHub

1. Go to https://github.com/new
2. Repository name: `kubernetes-learning` (or your preferred name)
3. Description: "Kubernetes learning environment with multi-service app for DevOps interview preparation"
4. Choose **Public** or **Private**
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

### Step 2: Push to GitHub

After creating the repo, GitHub will show you commands. Use these:

```bash
cd kubernetes-learning

# Add the remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/kubernetes-learning.git

# Rename branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

**Note**: You'll be prompted for your GitHub username and password (or personal access token).

## Option 2: Using GitHub Desktop

If you have GitHub Desktop installed:

1. Open GitHub Desktop
2. File → Add Local Repository
3. Choose the `kubernetes-learning` folder
4. Click "Publish repository"
5. Choose name and visibility
6. Click "Publish repository"

## Option 3: Using GitHub CLI (if you install it)

```bash
# Install GitHub CLI first, then:
cd kubernetes-learning
gh repo create kubernetes-learning --public --source=. --remote=origin --push
```

## Verify

After pushing, visit:
```
https://github.com/YOUR_USERNAME/kubernetes-learning
```

You should see all your files!

## Troubleshooting

### Authentication Issues

If you get authentication errors, you may need to use a Personal Access Token instead of a password:

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `repo` scope
3. Use the token as your password when pushing

### Branch Name

If you get errors about branch names:
```bash
git branch -M main  # Rename to main
git push -u origin main
```
