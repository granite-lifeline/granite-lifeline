"""
Data loader for dashboard.

Loads Report Layer output data for dashboard display.
"""

import json
from pathlib import Path
from typing import Dict, List, Any


def load_report_data(file_path: str) -> List[Dict[str, Any]]:
    """
    Load Report Layer output data from JSON file.
    
    Args:
        file_path: Path to JSON file containing report data
        
    Returns:
        List of report objects, each representing one monitored component
        
    Raises:
        FileNotFoundError: If file does not exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Report data file not found: {file_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Validate data is a list
    if not isinstance(data, list):
        raise ValueError("Report data must be a list of component reports")
    
    return data


def convert_to_component_dict(report_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Convert report list to component-keyed dictionary for dashboard use.
    
    Args:
        report_list: List of report objects from Report Layer
        
    Returns:
        Dictionary keyed by component name, values are report objects
    """
    component_dict = {}
    
    for report in report_list:
        component = report.get("component")
        if component:
            component_dict[component] = report
    
    return component_dict


def load_dashboard_data(file_path: str = "dashboard/tests/ui_required_data.json") -> Dict[str, Dict[str, Any]]:
    """
    Load and prepare report data for dashboard display.
    
    Args:
        file_path: Path to JSON file containing report data.
                   Defaults to dashboard test data.
        
    Returns:
        Dictionary keyed by component name, ready for dashboard use
        
    Example:
        >>> data = load_dashboard_data()
        >>> cooling_data = data["cooling_system_stress"]
        >>> print(cooling_data["risk_level"])
        'High'
    """
    report_list = load_report_data(file_path)
    return convert_to_component_dict(report_list)
