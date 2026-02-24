# Architecture Diagram

## Module Dependency Flow

```
┌─────────────────────────────────────────────────────────────┐
│                          main.py                             │
│  • Application Entry Point                                   │
│  • Navigation Logic                                          │
│  • Page Setup & Configuration                               │
└────────────┬────────────────┬──────────────┬────────────────┘
             │                │              │
             ▼                ▼              ▼
    ┌────────────┐   ┌────────────┐   ┌────────────┐
    │  views/    │   │components/ │   │constants.py│
    │            │   │            │   │            │
    │ • home     │   │ • action   │   │ • COLORS   │
    │ • simulator│   │   _button  │   │ • ANIMATION│
    │ • analytics│   │            │   │ • WINDOW   │
    └─────┬──────┘   └─────┬──────┘   └─────▲──────┘
          │                │                 │
          └────────────────┴─────────────────┘
                    Import Flow
```

## File Size Distribution

```
main.py (110 lines)              ████████░░░░░░░░░░░░░░░
constants.py (28 lines)          ██░░░░░░░░░░░░░░░░░░░░░
components/action_button.py      ███████████████░░░░░░░░
views/home.py                     ███████████░░░░░░░░░░░░
views/simulator.py                ██████████░░░░░░░░░░░░░
views/analytics.py                ████████████████████░░░
```

## Component Relationships

```
┌──────────────────────────────────────────────┐
│              User Interface                   │
└──────────────┬───────────────────────────────┘
               │
        ┌──────┴──────┐
        │             │
   ┌────▼─────┐  ┌───▼──────┐
   │Navigation│  │ Content  │
   │   Rail   │  │ Switcher │
   └──────────┘  └────┬─────┘
                      │
          ┌───────────┼───────────┐
          │           │           │
     ┌────▼────┐ ┌───▼────┐ ┌───▼─────┐
     │  Home   │ │Simulator│ │Analytics│
     │  View   │ │  View   │ │  View   │
     └────┬────┘ └────┬────┘ └────┬────┘
          │           │           │
          └───────────┴───────────┘
                      │
              ┌───────▼────────┐
              │ Action Button  │
              │   Component    │
              └────────────────┘
```

## Data Flow

```
User Click
    ↓
Navigation Rail
    ↓
on_nav_change()
    ↓
Update content_switcher.content
    ↓
Create View (home/simulator/analytics)
    ↓
Render Components (action_button, cards)
    ↓
Apply Styles (from constants.py)
    ↓
Display to User
    ↓
400ms Cross-Fade Animation
```

## Module Responsibilities

### main.py

```
┌─────────────────────────┐
│   Page Configuration    │
│   • Theme setup         │
│   • Window sizing       │
│   • Background color    │
├─────────────────────────┤
│  Navigation Management  │
│   • NavigationRail      │
│   • View switching      │
│   • AnimatedSwitcher    │
└─────────────────────────┘
```

### constants.py

```
┌─────────────────────────┐
│    Color Palette        │
│    Animation Timing     │
│    Window Settings      │
└─────────────────────────┘
        ▲
        │ (imported by all)
```

### components/

```
┌─────────────────────────┐
│   Reusable UI Parts     │
│   • action_button       │
│   • (future components) │
└─────────────────────────┘
```

### views/

```
┌─────────────────────────┐
│      home.py            │
│   create_home_view()    │
│   _create_feature_card()│
├─────────────────────────┤
│    simulator.py         │
│   create_simulator_view()│
│   _create_slider_control()│
├─────────────────────────┤
│    analytics.py         │
│   create_analytics_view()│
│   _create_metric_card() │
│   _create_achievement() │
└─────────────────────────┘
```

## Benefits Visualization

### Before: Monolithic

```
┌─────────────────┐
│                 │
│   main.py       │
│   (491 lines)   │
│                 │
│  Everything     │
│  in one file    │
│                 │
└─────────────────┘
```

### After: Modular

```
┌────────┐  ┌──────────┐  ┌───────────┐
│ main   │  │constants │  │components │
│(110 L) │  │ (28 L)   │  │  package  │
└───┬────┘  └────┬─────┘  └─────┬─────┘
    │            │              │
    └────────────┴──────────────┘
                 │
         ┌───────▼────────┐
         │ views package  │
         │  • home        │
         │  • simulator   │
         │  • analytics   │
         └────────────────┘
```

Organized • Maintainable • Scalable • Professional
