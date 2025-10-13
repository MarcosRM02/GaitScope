# 🚀 Quick Start - Heatmap Integration

## TL;DR

```bash
# 1. Validate installation
python test_heatmap_integration.py

# 2. Run application
python -m video_gait_analyzer.main

# 3. Load dataset with L.csv, R.csv, JSON files
# 4. Click "Load Dataset"
# 5. Click "▶ Play" in heatmap panel
# 6. Enjoy! 🔥
```

---

## 30-Second Setup

### Step 1: Test (5 seconds)

```bash
python test_heatmap_integration.py
```

**Expected**: `✓ 5/5 tests pasados`

### Step 2: Launch (5 seconds)

```bash
python -m video_gait_analyzer.main
```

### Step 3: Load Data (10 seconds)

1. Select dataset from dropdown
2. Click "Load Dataset" button
3. Wait for "Heatmap: XXX frames loaded"

### Step 4: Play Heatmap (5 seconds)

1. Find heatmap panel (lower right)
2. Click "▶ Play" button
3. Watch the magic! ✨

### Step 5: Customize (optional)

- **Faster**: Increase FPS spinbox
- **Slower**: Decrease FPS spinbox
- **Sync**: Check "Sync with video"

---

## Troubleshooting (1 minute)

### Problem: Tests fail

**Solution**:

```bash
# Check Heatmap_Project exists
ls Heatmap_Project/

# Should show: animator.py, heatmap.py, prerenderer.py
```

### Problem: No heatmap data loads

**Solution**: Dataset needs these files:

```
session_dir/
├── L.csv
├── R.csv
```

(Sensor coordinates are loaded automatically from video_gait_analyzer/in/)

### Problem: Animation is slow

**Solution**: Reduce FPS to 30 Hz or lower

### Problem: UI freezes

**Solution**: Restart application. If persists, check CPU usage.

---

## Key Controls

| Control        | Action                   |
| -------------- | ------------------------ |
| Heatmap ▶ Play | Start animation          |
| FPS Spinbox    | Change speed (1-120 Hz)  |
| Sync checkbox  | Link to video timeline   |
| Video ▶ Play   | Play video (independent) |

---

## File Locations

- **Code**: `video_gait_analyzer/core/heatmap_adapter.py`
- **Widget**: `video_gait_analyzer/widgets/heatmap_widget.py`
- **Utils**: `video_gait_analyzer/utils/heatmap_utils.py`
- **Docs**: `HEATMAP_INTEGRATION.md` (technical)
- **Guide**: `HEATMAP_USAGE.md` (user guide)

---

## Quick Validation Checklist

- [ ] Tests pass (5/5)
- [ ] Application opens
- [ ] Heatmap panel visible
- [ ] Data loads successfully
- [ ] Animation plays smoothly
- [ ] FPS control works
- [ ] Sync mode works

If all checked: **✅ You're good to go!**

---

## Need More Info?

- **Full guide**: `HEATMAP_USAGE.md`
- **Technical docs**: `HEATMAP_INTEGRATION.md`
- **Complete summary**: `IMPLEMENTATION_SUMMARY.md`
- **QA checklist**: `VERIFICATION_CHECKLIST.md`

---

**Happy analyzing! 🎉**
