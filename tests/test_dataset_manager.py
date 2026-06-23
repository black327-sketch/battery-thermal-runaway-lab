import pandas as pd
import streamlit as st

from app.utils.dataset_manager import (
    get_active_dataset_config,
    get_validated_status,
    list_available_datasets,
    load_active_arc_curve,
    load_active_gc_composition,
    set_active_dataset,
)


def setup_function():
    st.session_state.pop("active_dataset", None)


def test_active_dataset_defaults_to_teaching_demo():
    config = get_active_dataset_config()
    assert config["dataset_name"] == "teaching_demo"
    assert config["is_teaching_demo"]
    assert "非文献原始数据" in config["message"]


def test_list_available_datasets_includes_teaching_demo():
    df = list_available_datasets()
    assert "teaching_demo" in set(df["dataset_name"])
    assert bool(df.loc[df["dataset_name"].eq("teaching_demo"), "available"].iloc[0])


def test_validated_literature_missing_does_not_disguise_as_literature():
    set_active_dataset("validated_literature")
    config = get_active_dataset_config()
    assert config["dataset_name"] == "validated_literature"
    assert config["is_validated_literature"]
    assert "不完整" in config["message"] or config["missing_items"]


def test_teaching_demo_loaders_return_dataframes():
    set_active_dataset("teaching_demo")
    assert isinstance(load_active_arc_curve(), pd.DataFrame)
    assert isinstance(load_active_gc_composition(), pd.DataFrame)
    assert not load_active_arc_curve().empty


def test_validated_status_reports_required_files():
    status = get_validated_status()
    assert "literature_metadata" in set(status["数据项"])
    assert "状态" in status.columns
