"""
Templater — A1111 Extension
====================================
Adds a Templates tab to the Extra Networks panel (alongside LoRA, TI, etc).
Click a card to insert its tags into the prompt.
Gear icon shows section info.
Edit panel sits as an AlwaysVisible script below the prompt.
"""

import os
import json
import gradio as gr

import modules.scripts as scripts
from modules import script_callbacks, ui_extra_networks


# ---------------------------------------------------------------------------
# Template storage
# ---------------------------------------------------------------------------

TEMPLATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"
)
os.makedirs(TEMPLATES_DIR, exist_ok=True)


def list_templates() -> list[str]:
    return sorted(
        f.replace(".json", "")
        for f in os.listdir(TEMPLATES_DIR)
        if f.endswith(".json")
    )


def load_template(name: str) -> dict:
    path = os.path.join(TEMPLATES_DIR, f"{name}.json")
    if not os.path.exists(path):
        return {"name": name, "sections": []}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_template(template: dict) -> str:
    name = template["name"].strip()
    if not name:
        return "⚠️ Template name cannot be empty."
    path = os.path.join(TEMPLATES_DIR, f"{name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=2, ensure_ascii=False)
    return f"✅ Saved '{name}'"


def delete_template(name: str) -> str:
    path = os.path.join(TEMPLATES_DIR, f"{name}.json")
    if os.path.exists(path):
        os.remove(path)
        return f"🗑️ Deleted '{name}'"
    return f"⚠️ Template '{name}' not found."


def assemble_tags(template: dict) -> str:
    return ", ".join(
        s["tags"].strip()
        for s in template.get("sections", [])
        if s.get("tags", "").strip()
    )


# ---------------------------------------------------------------------------
# Extra Networks Page — the Templates tab
# ---------------------------------------------------------------------------

class ExtraNetworksPageTemplates(ui_extra_networks.ExtraNetworksPage):

    def __init__(self):
        super().__init__("Templates")

    def refresh(self):
        pass

    def create_item(self, name, index=None, enable_filter=True):
        tmpl = load_template(name)
        sections = tmpl.get("sections", [])
        tags = assemble_tags(tmpl)
        filename = os.path.join(TEMPLATES_DIR, f"{name}.json")
        path_no_ext = os.path.splitext(filename)[0]
        local_preview = f"{path_no_ext}.preview.png"

        section_lines = "\n".join(
            f"• {s['name']}: {s['tags']}" for s in sections
        )
        description = section_lines if section_lines else "No sections defined."

        return {
            "name": name,
            "filename": filename,
            "shorthash": None,
            "prompt": ui_extra_networks.quote_js(tags),
            "description": description,
            "search_terms": [self.search_terms_from_path(filename), name],
            "local_preview": local_preview,
            "preview": self.find_preview(path_no_ext),
            "sort_keys": {"default": index or 0},
        }

    def list_items(self):
        for index, name in enumerate(list_templates()):
            item = self.create_item(name, index)
            if item is not None:
                yield item

    def allowed_directories_for_previews(self):
        return [TEMPLATES_DIR]

    def create_user_metadata_editor(self, ui, tabname):
        if TemplateMetadataEditor is not None:
            return TemplateMetadataEditor(ui, tabname, self)
        return super().create_user_metadata_editor(ui, tabname)


def register_extra_network_page():
    ui_extra_networks.register_page(ExtraNetworksPageTemplates())


script_callbacks.on_before_ui(register_extra_network_page)


# ---------------------------------------------------------------------------
# Custom metadata editor — section editor inside the gear popup
# ---------------------------------------------------------------------------

try:
    from modules import ui_extra_networks_user_metadata

    MAX_POPUP_SECTIONS = 20

    class TemplateMetadataEditor(ui_extra_networks_user_metadata.UserMetadataEditor):

        def __init__(self, ui, tabname, page):
            super().__init__(ui, tabname, page)
            self.section_name_inputs  = []
            self.section_tags_inputs  = []
            self.section_rows         = []
            self.section_remove_btns  = []
            self.add_section_btn      = None
            self.visible_count        = None

        def create_extra_default_items_in_left_column(self):
            gr.Markdown("### Sections")
            self.add_section_btn = gr.Button("➕ Add section", variant="secondary", size="sm")

            for i in range(MAX_POPUP_SECTIONS):
                with gr.Row(visible=(i == 0)) as row:
                    sec_name = gr.Textbox(label=f"Section {i+1} name", scale=1, placeholder="e.g. Style")
                    sec_tags = gr.Textbox(label="Tags", scale=3, placeholder="e.g. anime, detailed")
                    rem_btn  = gr.Button("✕", scale=0, min_width=40, size="sm")
                self.section_name_inputs.append(sec_name)
                self.section_tags_inputs.append(sec_tags)
                self.section_rows.append(row)
                self.section_remove_btns.append(rem_btn)

        def put_values_into_components(self, name):
            parent_vals = list(super().put_values_into_components(name))

            tmpl = load_template(name)
            sections = tmpl.get("sections", [])
            n = len(sections)

            name_updates = [gr.update(value=sections[i]["name"] if i < n else "", visible=i < n) for i in range(MAX_POPUP_SECTIONS)]
            tags_updates = [gr.update(value=sections[i]["tags"]  if i < n else "", visible=i < n) for i in range(MAX_POPUP_SECTIONS)]
            row_updates  = [gr.update(visible=i < n) for i in range(MAX_POPUP_SECTIONS)]

            return parent_vals + [n] + name_updates + tags_updates + row_updates

        def save_user_metadata(self, name, desc, notes):
            super().save_user_metadata(name, desc, notes)

        def _save_with_sections(self, name, desc, notes, *section_data):
            self.save_user_metadata(name, desc, notes)
            # section_data = [visible_count, name0..nameN, tags0..tagsN]
            n     = int(section_data[0])
            rest  = section_data[1:]
            names = rest[:MAX_POPUP_SECTIONS]
            tags  = rest[MAX_POPUP_SECTIONS:]
            sections = [
                {"name": names[i], "tags": tags[i]}
                for i in range(n)
                if names[i].strip() or tags[i].strip()
            ]
            save_template({"name": name, "sections": sections})

        def create_editor(self):
            self.visible_count = gr.State(1)
            self.create_default_editor_elems()

            self.edit_notes = gr.TextArea(label='Notes', lines=4)

            self.create_default_buttons()

            self.button_edit\
                .click(
                    fn=self.put_values_into_components,
                    inputs=[self.edit_name_input],
                    outputs=[self.edit_name, self.edit_description, self.html_filedata,
                             self.html_preview, self.edit_notes, self.visible_count]
                            + self.section_name_inputs + self.section_tags_inputs + self.section_rows
                )\
                .then(fn=lambda: gr.update(visible=True), inputs=[], outputs=[self.box])

            self.setup_save_handler(
                self.button_save,
                self._save_with_sections,
                [self.edit_description, self.edit_notes, self.visible_count]
                + self.section_name_inputs + self.section_tags_inputs,
            )

            # Add section
            def add_section(n, *names_and_tags):
                new_n = min(n + 1, MAX_POPUP_SECTIONS)
                names = list(names_and_tags[:MAX_POPUP_SECTIONS])
                tags  = list(names_and_tags[MAX_POPUP_SECTIONS:])
                if new_n - 1 < MAX_POPUP_SECTIONS:
                    names[new_n - 1] = ""
                    tags[new_n - 1]  = ""
                return (
                    [new_n]
                    + [gr.update(visible=(i < new_n)) for i in range(MAX_POPUP_SECTIONS)]
                    + [gr.update(value=names[i], visible=(i < new_n)) for i in range(MAX_POPUP_SECTIONS)]
                    + [gr.update(value=tags[i],  visible=(i < new_n)) for i in range(MAX_POPUP_SECTIONS)]
                )

            self.add_section_btn.click(
                fn=add_section,
                inputs=[self.visible_count] + self.section_name_inputs + self.section_tags_inputs,
                outputs=[self.visible_count] + self.section_rows + self.section_name_inputs + self.section_tags_inputs,
            )

            # Remove section buttons
            for idx, rem_btn in enumerate(self.section_remove_btns):
                def make_remover(ridx):
                    def remove(n, *names_and_tags):
                        names = list(names_and_tags[:MAX_POPUP_SECTIONS])
                        tags  = list(names_and_tags[MAX_POPUP_SECTIONS:])
                        if ridx < len(names):
                            names.pop(ridx)
                            tags.pop(ridx)
                        new_n = max(1, n - 1)
                        names = (names + [""] * MAX_POPUP_SECTIONS)[:MAX_POPUP_SECTIONS]
                        tags  = (tags  + [""] * MAX_POPUP_SECTIONS)[:MAX_POPUP_SECTIONS]
                        return (
                            [new_n]
                            + [gr.update(visible=(i < new_n)) for i in range(MAX_POPUP_SECTIONS)]
                            + [gr.update(value=names[i], visible=(i < new_n)) for i in range(MAX_POPUP_SECTIONS)]
                            + [gr.update(value=tags[i],  visible=(i < new_n)) for i in range(MAX_POPUP_SECTIONS)]
                        )
                    return remove

                rem_btn.click(
                    fn=make_remover(idx),
                    inputs=[self.visible_count] + self.section_name_inputs + self.section_tags_inputs,
                    outputs=[self.visible_count] + self.section_rows + self.section_name_inputs + self.section_tags_inputs,
                )

    def on_ui_tabs_templates():
        pass  # editor is created per-page, no tab needed here

except ImportError:
    print("[templater] ui_extra_networks_user_metadata not available — gear popup editor disabled")
    TemplateMetadataEditor = None


# ---------------------------------------------------------------------------
# AlwaysVisible Script — editor panel below the prompt
# ---------------------------------------------------------------------------

MAX_SECTIONS = 20


class TemplaterScript(scripts.Script):

    def title(self):
        return "Templater"

    def show(self, is_img2img):
        return False

    def ui(self, is_img2img):
        with gr.Accordion("🗂️ Templater", open=False):

            # ── Template selector ────────────────────────────────────────────
            with gr.Row():
                template_dropdown = gr.Dropdown(
                    label="Load template",
                    choices=list_templates(),
                    value=None,
                    scale=3,
                )
                refresh_btn = gr.Button("🔄", scale=0, min_width=40)

            status = gr.Textbox(label="Status", interactive=False, max_lines=1, visible=False)

            gr.Markdown("---")

            # ── Active template toggle view ──────────────────────────────────
            gr.Markdown("### Active template")
            assembled_preview = gr.Textbox(
                label="Assembled tags (will be appended to prompt on Generate)",
                interactive=False,
                lines=2,
            )
            TemplaterScript._assembled_preview = assembled_preview

            section_toggles = []
            for i in range(MAX_SECTIONS):
                with gr.Row(visible=False) as toggle_row:
                    enabled = gr.Checkbox(label="", value=True, scale=0, min_width=40)
                    sec_label = gr.Textbox(
                        value=f"Section {i+1}",
                        interactive=False,
                        label="Section",
                        scale=1,
                    )
                    sec_tags = gr.Textbox(
                        value="",
                        interactive=True,
                        label="Tags",
                        scale=3,
                    )
                section_toggles.append((toggle_row, enabled, sec_label, sec_tags))

            gr.Markdown("---")

            # ── Editor ───────────────────────────────────────────────────────
            gr.Markdown("### ✏️ Create / Edit Template")
            template_name_input = gr.Textbox(
                label="Template name",
                placeholder="e.g. Anime Portrait",
            )
            add_section_btn = gr.Button("➕ Add section", variant="secondary")

            section_rows = []
            for i in range(MAX_SECTIONS):
                with gr.Row(visible=(i == 0)) as row:
                    section_name = gr.Textbox(
                        label=f"Section {i+1} name",
                        placeholder="e.g. Subject",
                        scale=1,
                    )
                    section_tags = gr.Textbox(
                        label="Tags",
                        placeholder="e.g. 1girl, solo, detailed face",
                        scale=3,
                    )
                    remove_btn = gr.Button("✕", scale=0, min_width=40)
                section_rows.append((row, section_name, section_tags, remove_btn))

            with gr.Row():
                save_btn = gr.Button("💾 Save template", variant="primary", scale=3)
                delete_btn = gr.Button("🗑️", scale=0, min_width=42, variant="stop")

            delete_confirm_state = gr.State(False)

            # ── State ────────────────────────────────────────────────────────
            active_template_state = gr.State({"name": "", "sections": []})
            visible_sections_state = gr.State(1)

            # ── Component lists ──────────────────────────────────────────────
            toggle_row_components    = [t[0] for t in section_toggles]
            toggle_check_components  = [t[1] for t in section_toggles]
            toggle_label_components  = [t[2] for t in section_toggles]
            toggle_tag_components    = [t[3] for t in section_toggles]
            editor_row_components    = [s[0] for s in section_rows]
            editor_name_components   = [s[1] for s in section_rows]
            editor_tag_components    = [s[2] for s in section_rows]

            # ── Wiring ───────────────────────────────────────────────────────

            def refresh_templates():
                return gr.update(choices=list_templates())

            refresh_btn.click(refresh_templates, outputs=[template_dropdown])

            def update_preview(*args):
                checks = args[:MAX_SECTIONS]
                tags   = args[MAX_SECTIONS:]
                parts  = [t.strip() for c, t in zip(checks, tags) if c and t.strip()]
                return ", ".join(parts)

            for _, enabled, _, sec_tags in section_toggles:
                enabled.change(update_preview,
                    inputs=toggle_check_components + toggle_tag_components,
                    outputs=[assembled_preview])
                sec_tags.change(update_preview,
                    inputs=toggle_check_components + toggle_tag_components,
                    outputs=[assembled_preview])

            def on_load_template(name):
                if not name:
                    empty = [{"name": "", "sections": []}]
                    empty += [gr.update(visible=False)] * MAX_SECTIONS
                    empty += [gr.update(value="")] * MAX_SECTIONS
                    empty += [gr.update(value="")] * MAX_SECTIONS
                    empty += [gr.update(value=True)] * MAX_SECTIONS
                    empty += [gr.update(value=""), gr.update(value=1), gr.update(value="")]
                    empty += [gr.update(visible=False)] * MAX_SECTIONS
                    empty += [gr.update(value="")] * MAX_SECTIONS
                    empty += [gr.update(value="")] * MAX_SECTIONS
                    return empty

                tmpl = load_template(name)
                sections = tmpl.get("sections", [])
                n = len(sections)

                out = [tmpl]
                out += [gr.update(visible=(i < n)) for i in range(MAX_SECTIONS)]
                out += [gr.update(value=sections[i]["name"] if i < n else "") for i in range(MAX_SECTIONS)]
                out += [gr.update(value=sections[i]["tags"]  if i < n else "") for i in range(MAX_SECTIONS)]
                out += [gr.update(value=True) for _ in range(MAX_SECTIONS)]
                out += [gr.update(value=name), gr.update(value=n)]
                assembled = ", ".join(s["tags"] for s in sections if s["tags"].strip())
                out += [gr.update(value=assembled)]
                out += [gr.update(visible=(i < n)) for i in range(MAX_SECTIONS)]
                out += [gr.update(value=sections[i]["name"] if i < n else "") for i in range(MAX_SECTIONS)]
                out += [gr.update(value=sections[i]["tags"]  if i < n else "") for i in range(MAX_SECTIONS)]
                return out

            template_dropdown.change(
                on_load_template,
                inputs=[template_dropdown],
                outputs=[active_template_state]
                    + toggle_row_components
                    + toggle_label_components
                    + toggle_tag_components
                    + toggle_check_components
                    + [template_name_input, visible_sections_state, assembled_preview]
                    + editor_row_components
                    + editor_name_components
                    + editor_tag_components,
            )

            # Reset delete confirm when switching templates
            template_dropdown.change(
                lambda _: (False, gr.update(value="🗑️")),
                inputs=[template_dropdown],
                outputs=[delete_confirm_state, delete_btn],
            )

            def add_section(n):
                new_n = min(n + 1, MAX_SECTIONS)
                return [new_n] + [gr.update(visible=(i < new_n)) for i in range(MAX_SECTIONS)]

            add_section_btn.click(
                add_section,
                inputs=[visible_sections_state],
                outputs=[visible_sections_state] + editor_row_components,
            )

            for idx, (_, _, _, remove_btn) in enumerate(section_rows):
                def make_remover(ridx):
                    def remove(n, *names_and_tags):
                        names = list(names_and_tags[:MAX_SECTIONS])
                        tags  = list(names_and_tags[MAX_SECTIONS:])
                        if ridx < len(names):
                            names.pop(ridx)
                            tags.pop(ridx)
                        new_n = max(1, n - 1)
                        names = (names + [""] * MAX_SECTIONS)[:MAX_SECTIONS]
                        tags  = (tags  + [""] * MAX_SECTIONS)[:MAX_SECTIONS]
                        return ([new_n]
                            + [gr.update(visible=(i < new_n)) for i in range(MAX_SECTIONS)]
                            + [gr.update(value=names[i]) for i in range(MAX_SECTIONS)]
                            + [gr.update(value=tags[i])  for i in range(MAX_SECTIONS)])
                    return remove
                remove_btn.click(
                    make_remover(idx),
                    inputs=[visible_sections_state] + editor_name_components + editor_tag_components,
                    outputs=[visible_sections_state] + editor_row_components + editor_name_components + editor_tag_components,
                )

            def on_save(tmpl_name, n_visible, active_tmpl, *names_and_tags):
                names = names_and_tags[:MAX_SECTIONS]
                tags  = names_and_tags[MAX_SECTIONS:]
                sections = [
                    {"name": names[i], "tags": tags[i]}
                    for i in range(n_visible)
                    if names[i].strip() or tags[i].strip()
                ]
                tmpl = {"name": tmpl_name.strip(), "sections": sections}
                msg = save_template(tmpl)

                out = [msg, gr.update(choices=list_templates(), value=tmpl_name.strip()), gr.update(visible=True)]

                if tmpl_name.strip() == active_tmpl.get("name", ""):
                    n = len(sections)
                    out += [gr.update(visible=(i < n)) for i in range(MAX_SECTIONS)]
                    out += [gr.update(value=sections[i]["name"] if i < n else "") for i in range(MAX_SECTIONS)]
                    out += [gr.update(value=sections[i]["tags"]  if i < n else "") for i in range(MAX_SECTIONS)]
                    assembled = ", ".join(s["tags"] for s in sections if s["tags"].strip())
                    out += [gr.update(value=assembled)]
                else:
                    out += [gr.update()] * (MAX_SECTIONS * 3 + 1)

                return out

            save_btn.click(
                on_save,
                inputs=[template_name_input, visible_sections_state, active_template_state]
                    + editor_name_components + editor_tag_components,
                outputs=[status, template_dropdown, status]
                    + toggle_row_components
                    + toggle_label_components
                    + toggle_tag_components
                    + [assembled_preview],
            )

            save_btn.click(
                lambda tmpl_name, n, *nat: {"name": tmpl_name.strip(), "sections": [
                    {"name": nat[i], "tags": nat[MAX_SECTIONS+i]}
                    for i in range(n) if nat[i].strip() or nat[MAX_SECTIONS+i].strip()
                ]},
                inputs=[template_name_input, visible_sections_state] + editor_name_components + editor_tag_components,
                outputs=[active_template_state],
            )

            def on_delete_click(name, confirmed):
                if not name:
                    return False, gr.update(), gr.update(value="⚠️ No template selected.", visible=True), gr.update()
                if not confirmed:
                    return True, gr.update(), gr.update(value=f"⚠️ Click 🗑️ again to delete '{name}'", visible=True), gr.update(value="❗ Confirm?")
                msg = delete_template(name)
                return False, gr.update(choices=list_templates(), value=None), gr.update(value=msg, visible=True), gr.update(value="🗑️")

            delete_btn.click(
                on_delete_click,
                inputs=[template_dropdown, delete_confirm_state],
                outputs=[delete_confirm_state, template_dropdown, status, delete_btn],
            )

        return toggle_check_components + toggle_tag_components + [assembled_preview]

    def process(self, p, *args):
        checks   = args[:MAX_SECTIONS]
        tags     = args[MAX_SECTIONS:MAX_SECTIONS*2]
        extra = ", ".join(t.strip() for c, t in zip(checks, tags) if c and t.strip())
        if extra:
            existing   = {t.strip().lower() for t in p.prompt.split(",") if t.strip()}
            new_tokens = [t.strip() for t in extra.split(",") if t.strip() and t.strip().lower() not in existing]
            if new_tokens:
                if p.prompt.strip():
                    p.prompt = p.prompt.rstrip(", ") + ", " + ", ".join(new_tokens)
                else:
                    p.prompt = ", ".join(new_tokens)

    # Grab txt2img prompt and generate button
    txt2img_prompt   = None
    txt2img_generate = None

    def after_component(self, component, **kwargs):
        if kwargs.get("elem_id") == "txt2img_prompt":
            TemplaterScript.txt2img_prompt = component
        if kwargs.get("elem_id") == "txt2img_generate":
            TemplaterScript.txt2img_generate = component


def on_app_started(demo, app):
    prompt   = TemplaterScript.txt2img_prompt
    generate = TemplaterScript.txt2img_generate
    preview  = getattr(TemplaterScript, "_assembled_preview", None)

    if not all([prompt, generate, preview]):
        return

    def do_paste(current_prompt, assembled):
        assembled = assembled.strip()
        if not assembled:
            return current_prompt
        existing   = {t.strip().lower() for t in current_prompt.split(",") if t.strip()}
        new_tokens = [t.strip() for t in assembled.split(",") if t.strip() and t.strip().lower() not in existing]
        if not new_tokens:
            return current_prompt
        if current_prompt.strip():
            return current_prompt.rstrip(", ") + ", " + ", ".join(new_tokens)
        return ", ".join(new_tokens)

    with demo:
        generate.click(do_paste, inputs=[prompt, preview], outputs=[prompt])


script_callbacks.on_app_started(on_app_started)