
# Workshop Setup Panel (Drop‑in)

This package adds the converted Streamlit functionality to your **existing PyQt6 app**
without changing your **tabs**, **theme**, or **login**.

## Quick integration

1. Ensure deps are installed:

```
pip install pydantic[email] python-dotenv openai pyyaml
```

2. In your main window (where you construct your `QTabWidget`), add:

```python
from workshop import WorkshopSetupPanel

# ... after your tabs are created
self.tabs.addTab(WorkshopSetupPanel(self), "Workshop Setup")
```

The panel follows your app's theme automatically. It also works **offline**
(without an `OPENAI_API_KEY`) and will generate stubbed content so the UI remains usable.

### Optional: Export helper

If you want a "Download JSON" button in your host app, call:

```python
panel = WorkshopSetupPanel(self)
# ...
panel.export_state("workshop_state.json")
```

No other parts of your app are modified.
