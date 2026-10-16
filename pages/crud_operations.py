"""CRUD Operations page: form-based Create / Read / Update / Delete."""
from datetime import date
from typing import Any

import streamlit as st

from utils import crud
from utils.db_connection import DatabaseError

st.title("🛠️ CRUD Operations")
st.caption("Manage records with validated forms. Every write runs inside a database transaction.")

entity = st.selectbox("Table", list(crud.ENTITIES))
cfg = crud.ENTITIES[entity]


def render_form(defaults: dict[str, Any] | None, key: str) -> dict[str, Any]:
    """Build input widgets from the entity config and return the entered values."""
    defaults = defaults or {}
    values: dict[str, Any] = {}
    for f in cfg["fields"]:
        name, label, kind = f["name"], f["label"] + (" *" if f["required"] else ""), f["kind"]
        current = defaults.get(name)
        wkey = f"{key}_{name}"
        if kind == "text":
            values[name] = st.text_input(label, value=current or "", key=wkey)
        elif kind in ("int", "float"):
            cast = int if kind == "int" else float
            values[name] = st.number_input(
                label, value=cast(current) if current is not None else None,
                min_value=cast(f.get("min", 0)), step=cast(1) if kind == "int" else 0.01, key=wkey)
        elif kind == "select":
            options = list(f["options"]) if f["required"] else [None, *f["options"]]
            idx = options.index(current) if current in options else 0
            values[name] = st.selectbox(label, options, index=idx, key=wkey,
                                        format_func=lambda o: "-" if o is None else o)
        elif kind == "fk":
            opts = crud.fk_options(f["fk"])
            options = list(opts) if f["required"] else [None, *opts]
            idx = options.index(current) if current in options else 0
            values[name] = st.selectbox(label, options, index=idx, key=wkey,
                                        format_func=lambda o, m=opts: "-" if o is None else m.get(o, str(o)))
        elif kind == "date":
            parsed = date.fromisoformat(str(current)[:10]) if current else (date.today() if f["required"] else None)
            values[name] = st.date_input(label, value=parsed, key=wkey)
    return values


def record_picker(key: str) -> int | None:
    """Select an existing record; returns its primary key."""
    rows = crud.list_rows(entity, st.text_input("🔎 Filter by name/description", key=f"{key}_search"), limit=200)
    if rows.empty:
        st.info("No records found.")
        return None
    labels = {int(r[cfg["pk"]]): f"#{int(r[cfg['pk']])} - {r[cfg['label']]}" for _, r in rows.iterrows()}
    return st.selectbox("Select record", list(labels), format_func=labels.get, key=f"{key}_pick")


tab_read, tab_create, tab_update, tab_delete = st.tabs(["📖 Read", "➕ Create", "✏️ Update", "🗑️ Delete"])

try:
    with tab_read:
        search = st.text_input("🔎 Search", key="read_search")
        df = crud.list_rows(entity, search, limit=500)
        st.caption(f"{len(df)} record(s) shown (max 500, newest first)")
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tab_create:
        with st.form(f"create_{entity}", clear_on_submit=False):
            new_values = render_form(None, f"c_{entity}")
            submitted = st.form_submit_button("Create record", type="primary")
        if submitted:
            errors = crud.validate(entity, new_values)
            if errors:
                for e in errors:
                    st.error(e)
            else:
                try:
                    new_id = crud.create_row(entity, new_values)
                    st.success(f"✅ Created record #{new_id}.")
                except (DatabaseError, ValueError) as exc:
                    st.error(f"Could not create record: {exc}")

    with tab_update:
        pk = record_picker(f"u_{entity}")
        if pk is not None:
            row = crud.get_row(entity, pk)
            with st.form(f"update_{entity}_{pk}"):
                upd_values = render_form(row, f"u_{entity}_{pk}")
                submitted = st.form_submit_button("Save changes", type="primary")
            if submitted:
                errors = crud.validate(entity, upd_values)
                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    try:
                        crud.update_row(entity, pk, upd_values)
                        st.success(f"✅ Record #{pk} updated.")
                    except (DatabaseError, ValueError) as exc:
                        st.error(f"Could not update record: {exc}")

    with tab_delete:
        pk = record_picker(f"d_{entity}")
        if pk is not None:
            st.json(crud.get_row(entity, pk), expanded=False)
            confirm = st.checkbox("I understand this permanently deletes the record", key=f"confirm_{entity}_{pk}")
            if st.button("Delete record", type="primary", disabled=not confirm):
                try:
                    crud.delete_row(entity, pk)
                    st.success(f"🗑️ Record #{pk} deleted.")
                    st.rerun()
                except DatabaseError as exc:
                    st.error(str(exc))
except DatabaseError as exc:
    st.error(f"Database error: {exc}")
