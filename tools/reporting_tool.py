import os
from datetime import datetime
from langchain_core.tools import tool

REPORTS_DIR = "reports"

@tool
def generate_report(title: str, content: str) -> str:
    """Generates a markdown report file and saves it to the reports folder."""
    if not os.path.exists(REPORTS_DIR):
        os.makedirs(REPORTS_DIR)
        
    # Clean up filename
    safe_title = "".join([c if c.isalnum() or c in [' ', '_', '-'] else "" for c in title]).strip().replace(" ", "_")
    filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    file_path = os.path.join(REPORTS_DIR, filename)
    
    report_content = f"""# {title}
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Role: Autonomous Business Operations Agent (AI Employee)

---

{content}

---
*Report generated automatically.*
"""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        return f"Report successfully generated and saved to {file_path}."
    except Exception as e:
        return f"Failed to generate report: {e}"
