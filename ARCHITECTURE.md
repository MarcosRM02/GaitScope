# Architecture Documentation

## Overview

The Video Gait Analyzer is built using a clean, modular architecture that separates concerns and promotes maintainability and scalability.

## Design Principles

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Modularity**: Components can be developed, tested, and modified independently
3. **Loose Coupling**: Minimal dependencies between modules
4. **High Cohesion**: Related functionality grouped together
5. **Dependency Injection**: Controllers and managers are injected, not created internally

## Architecture Layers

```
┌─────────────────────────────────────────────┐
│           User Interface Layer              │
│         (video_player.py + widgets)         │
└─────────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────┐
│          Application Logic Layer            │
│  ┌────────────┐  ┌──────────┐  ┌─────────┐ │
│  │   Video    │  │   Data   │  │  Plot   │ │
│  │ Controller │  │ Manager  │  │ Manager │ │
│  └────────────┘  └──────────┘  └─────────┘ │
└─────────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────┐
│            Data/Service Layer               │
│    (OpenCV, Pandas, PyQtGraph, Qt)          │
└─────────────────────────────────────────────┘
```

## Core Components

### 1. VideoPlayer (Main Window)

**Responsibility**: Coordinate all components and manage UI

**Key Features**:

- Builds and manages the user interface
- Coordinates VideoController, DataManager, and PlotManager
- Handles user input events
- Manages application state

**Design Pattern**: Mediator Pattern

- Acts as central coordinator
- Other components don't know about each other
- All communication flows through VideoPlayer

### 2. VideoController

**Responsibility**: Manage video playback operations

**Key Features**:

- Load/release video files
- Frame navigation and seeking
- Playback control (play/pause/stop)
- Speed control

**Design Pattern**: Controller Pattern

- Encapsulates video-related logic
- Provides clean API for video operations
- Manages internal state independently

**API**:

```python
controller = VideoController()
controller.load_video(path)
controller.seek_to_frame(100)
ret, frame = controller.read_frame()
```

### 3. DataManager

**Responsibility**: Load and process all data files

**Key Features**:

- CSV data loading and processing
- GaitRite data management
- Data transformation (grouping, summing)
- Video-to-CSV index mapping

**Design Pattern**: Repository Pattern

- Abstracts data access
- Provides uniform interface for data operations
- Handles data processing internally

**API**:

```python
manager = DataManager()
manager.load_csv_data(csv_L, csv_R)
manager.load_gaitrite_data(directory)
idx = manager.video_frame_to_csv_index(frame, fps)
```

### 4. PlotManager

**Responsibility**: Handle all visualization and plotting

**Key Features**:

- Create and update plots
- Cursor synchronization
- GaitRite footprint rendering
- Visual element management

**Design Pattern**: Manager Pattern

- Manages complex plot state
- Encapsulates PyQtGraph details
- Provides high-level plotting operations

**API**:

```python
manager = PlotManager(plot_widget, gaitrite_plot)
manager.create_csv_plots(x_data, sums_L, sums_R)
manager.update_cursor_position(time, sums_L, sums_R, idx)
```

## Data Flow

### Video Playback Flow

```
User Action (Play)
    → VideoPlayer.toggle_play_pause()
    → VideoController.is_playing = True
    → Timer starts
    → VideoController.advance_frame()
    → VideoPlayer._display_frame()
    → VideoPlayer._update_csv_cursor_from_video()
    → DataManager.video_frame_to_csv_index()
    → PlotManager.update_cursor_position()
```

### Dataset Loading Flow

```
User Selects Dataset
    → VideoPlayer.on_load_dataset_clicked()
    → VideoPlayer.configure_dataset_from_path()
    → find_video_file() [utils]
    → find_csv_file() [utils]
    → VideoController.load_video()
    → DataManager.load_csv_data()
    → DataManager.load_gaitrite_data()
    → PlotManager.create_csv_plots()
    → PlotManager.draw_gaitrite_footprints()
```

## Key Design Decisions

### 1. Why Separate Controllers?

**Problem**: Original monolithic class (1963 lines) was hard to maintain

**Solution**: Extract specific responsibilities into focused classes

**Benefits**:

- Each class < 300 lines
- Easy to test in isolation
- Clear API boundaries
- Can replace implementations without affecting others

### 2. Why Manager Pattern for Plots?

**Problem**: Complex plot state and many PyQtGraph operations

**Solution**: Encapsulate all plotting logic in PlotManager

**Benefits**:

- VideoPlayer doesn't need PyQtGraph knowledge
- Plot logic can be modified without touching UI
- Easy to add new plot types

### 3. Why Dependency Injection?

**Problem**: Tight coupling between components

**Solution**: Inject dependencies through constructors

**Example**:

```python
# Before (tight coupling)
class VideoPlayer:
    def __init__(self):
        self.plot = pg.PlotWidget()  # creates directly

# After (loose coupling)
class PlotManager:
    def __init__(self, plot_widget):
        self.plot_widget = plot_widget  # injected
```

**Benefits**:

- Easy to test (can inject mocks)
- Flexible configuration
- Components don't create dependencies

### 4. Why Constants Module?

**Problem**: Magic numbers scattered throughout code

**Solution**: Centralize all configuration in constants.py

**Benefits**:

- Single source of truth
- Easy to modify settings
- Self-documenting code

## Extension Points

### Adding New Data Sources

1. Create loader method in `DataManager`
2. Add data processing logic
3. Update `PlotManager` to visualize
4. No changes to `VideoPlayer` needed

### Adding New Visualizations

1. Add plot widget to UI in `VideoPlayer._build_ui()`
2. Create manager method in `PlotManager`
3. Call from `VideoPlayer` when needed

### Adding New Video Operations

1. Add method to `VideoController`
2. Call from `VideoPlayer` event handlers
3. No changes to other components

## Testing Strategy

### Unit Tests

- Test each component in isolation
- Mock dependencies
- Focus on business logic

Example:

```python
def test_video_frame_to_csv_index():
    manager = DataManager()
    manager.csv_sampling_rate = 64.0
    idx = manager.video_frame_to_csv_index(30, 30.0)
    assert idx == 64  # 1 second at 64 Hz
```

### Integration Tests

- Test component interactions
- Use real (but small) data files
- Verify data flow

### UI Tests

- Use pytest-qt for Qt testing
- Test user interactions
- Verify UI updates

## Performance Considerations

### Video Display

- Resize frames with OpenCV (faster than Qt)
- Cache last frame for exports
- Throttle seek operations during drag

### Plot Updates

- Throttle cursor updates (20 Hz max)
- Update only visible markers
- Use PyQtGraph's optimized rendering

### Data Loading

- Lazy load GaitRite data
- Process CSV in chunks if needed
- Cache processed data arrays

## Error Handling

### Graceful Degradation

- Continue if optional data missing
- Show placeholders for missing plots
- Log errors without crashing

### User Feedback

- Status bar messages for actions
- Dialog boxes for critical errors
- Console logging for debugging

## Future Enhancements

### Planned Features

1. **Export functionality**: Save annotated frames
2. **Analysis tools**: Measure distances, angles
3. **Comparison mode**: Side-by-side datasets
4. **Plugin system**: Extensible architecture

### Refactoring Opportunities

1. Extract UI building to separate module
2. Add configuration file support
3. Implement undo/redo for annotations
4. Add data export utilities

## Conclusion

This architecture provides:

- ✅ **Maintainability**: Small, focused modules
- ✅ **Testability**: Isolated components
- ✅ **Scalability**: Easy to extend
- ✅ **Readability**: Clear separation of concerns
- ✅ **Flexibility**: Swap implementations easily

The modular design ensures the codebase remains manageable as features are added and requirements evolve.
