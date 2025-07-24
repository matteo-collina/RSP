# Development Branch Guidelines

This is the **development branch** for GPSP Image Processor. 

## 🚧 Development Status
- **Current Dev Version**: 0.2.0-dev
- **Based on Stable**: v0.1.0
- **Target Features**: New enhancements and improvements

## 🔄 Development Workflow

### Working on Features
1. **Stay on dev branch**: Always develop new features here
2. **Regular commits**: Make frequent, small commits with clear messages
3. **Test thoroughly**: Ensure new features don't break existing functionality

### Merging to Main
When you're ready to release new features:

```bash
# 1. Switch to main and pull latest
git checkout main
git pull origin main

# 2. Merge dev into main
git merge dev

# 3. Update version (remove -dev suffix)
# Edit config/settings.py: "0.2.0-dev" → "0.2.0"

# 4. Create new release tag
git tag -a v0.2.0 -m "Release v0.2.0: [Your new features]"
git push origin v0.2.0
git push origin main

# 5. Switch back to dev and bump version
git checkout dev
# Edit config/settings.py: "0.2.0" → "0.3.0-dev"
```

### Emergency Hotfixes
For urgent fixes to the stable version:
```bash
# Create hotfix branch from main
git checkout main
git checkout -b hotfix-v0.1.1

# Make your fix, test, then merge to both main and dev
git checkout main
git merge hotfix-v0.1.1
git checkout dev
git merge hotfix-v0.1.1
```

## 📋 Development Checklist
- [ ] New features are thoroughly tested
- [ ] No breaking changes to existing functionality
- [ ] Documentation updated if needed
- [ ] Version number follows semantic versioning
- [ ] Ready for production use

## 🎯 Next Development Goals
Add your planned features here:
- [ ] Enhanced Metashape automation
- [ ] Additional image enhancement algorithms
- [ ] Improved batch processing workflows
- [ ] Performance optimizations
- [ ] Better error handling and logging

---
**Remember**: The `main` branch should always be in a stable, releasable state!
