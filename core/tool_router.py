import re
import webbrowser

from config.settings import BASE_DIR
from device.controller_factory import create_device_controller


class ToolRouter:

    def __init__(self, controller=None):

        self.projects_dir = BASE_DIR / "projects"
        self.projects_dir.mkdir(parents=True, exist_ok=True)

        # Device-specific execution controller.
        # Windows remains the default until other clients are implemented.
        self.controller = (
    controller
    if controller is not None
    else create_device_controller()
)

    def execute(self, action, **kwargs):

        action = str(action).strip().lower()

        if action == "open_app":
            return self.open_app(kwargs.get("app_name", ""))

        if action == "open_website":
            return self.open_website(kwargs.get("website", ""))

        if action == "create_website":
            return self.create_website(
                project_name=kwargs.get("project_name", "my_website"),
                html=kwargs.get("html", ""),
                css=kwargs.get("css", ""),
                javascript=kwargs.get("javascript", ""),
                open_after_create=kwargs.get("open_after_create", True)
            )

        if action == "save_memory":
            return self.save_memory(
                content=kwargs.get("content", ""),
                category=kwargs.get("category", "general"),
                importance=kwargs.get("importance", 2),
                is_core=kwargs.get("is_core", False)
            )

        return {
            "success": False,
            "message": f"Unknown action: {action}"
        }

    def save_memory(self, content, category="general", importance=2, is_core=False):
        from memory.memory_manager import MemoryManager
        mgr = MemoryManager()
        if not content or not str(content).strip():
            return {"success": False, "message": "Memory content cannot be empty."}
        if is_core:
            ok = mgr.remember_core(content=content, category=category, importance=importance)
        else:
            ok = mgr.remember(content=content, category=category, importance=importance)
        if ok:
            return {
                "success": True,
                "message": f"Successfully remembered: {content}",
                "category": category,
                "is_core": is_core
            }
        return {"success": False, "message": "Failed to save memory."}

    def open_app(self, app_name):
        return self.controller.open_app(app_name)

    def open_website(self, website):
        return self.controller.open_website(website)

    def clean_project_name(self, name):

        name = str(name).strip().lower()

        name = re.sub(r"[^a-z0-9_-]+", "_", name)
        name = name.strip("_-")

        return name or "my_website"

    def create_website(
        self,
        project_name,
        html,
        css="",
        javascript="",
        open_after_create=True
    ):

        if not html or not str(html).strip():
            return {
                "success": False,
                "message": "Website HTML content is missing."
            }

        try:
            project_name = self.clean_project_name(project_name)
            project_path = self.projects_dir / project_name

            # Keep website updates in the existing project.
            project_path.mkdir(parents=True, exist_ok=True)

            html_path = project_path / "index.html"
            css_path = project_path / "style.css"
            js_path = project_path / "script.js"

            html_content = str(html).strip()
            css_content = str(css or "").strip()
            js_content = str(javascript or "").strip()

            if css_content and "style.css" not in html_content:
                css_reference = (
                    '<link rel="stylesheet" href="style.css">'
                )

                position = html_content.lower().find("</head>")

                if position >= 0:
                    html_content = (
                        html_content[:position]
                        + css_reference
                        + "\n"
                        + html_content[position:]
                    )
                else:
                    html_content = css_reference + "\n" + html_content

            if js_content and "script.js" not in html_content:
                js_reference = (
                    '<script src="script.js"></script>'
                )

                position = html_content.lower().rfind("</body>")

                if position >= 0:
                    html_content = (
                        html_content[:position]
                        + js_reference
                        + "\n"
                        + html_content[position:]
                    )
                else:
                    html_content += "\n" + js_reference

            if css_content:
                css_path.write_text(css_content, encoding="utf-8")

            if js_content:
                js_path.write_text(js_content, encoding="utf-8")

            html_path.write_text(html_content, encoding="utf-8")

            if open_after_create:
                webbrowser.open(html_path.resolve().as_uri())

            return {
                "success": True,
                "message": "Website created or updated successfully.",
                "project_name": project_path.name,
                "project_path": str(project_path),
                "html_file": str(html_path),
                "css_file": str(css_path) if css_content else None,
                "javascript_file": str(js_path) if js_content else None
            }

        except Exception as error:
            return {
                "success": False,
                "message": f"Website creation failed: {error}"
            }