"""
Utilities for managing PDF form data sources.
Supports linked field functionality.
"""


class DataSourceUtils:
    """Utilities for working with form data sources."""

    @staticmethod
    def get_data_source(form_config, source_name):
        """
        Get a data source by name.

        Args:
            form_config (dict): Complete form configuration
            source_name (str): Name of the data source

        Returns:
            list: Data source items or empty list if not found
        """
        if not isinstance(form_config, dict):
            return []

        data_sources = form_config.get('data_sources', {})
        return data_sources.get(source_name, [])

    @staticmethod
    def get_field_choices_from_source(form_config, field_config):
        """
        Generate field choices from a data source.

        Args:
            form_config (dict): Complete form configuration
            field_config (dict): Field configuration

        Returns:
            list: List of choices for the field, or None if not using data source
        """
        data_source = field_config.get('data_source')
        data_source_key = field_config.get('data_source_key')

        if not data_source or not data_source_key:
            return None

        # Get the data source
        source_items = DataSourceUtils.get_data_source(form_config, data_source)

        # Extract unique values for this key
        choices = []
        seen = set()
        for item in source_items:
            value = item.get(data_source_key)
            if value is not None and value not in seen:
                choices.append(value)
                seen.add(value)

        return choices

    @staticmethod
    def get_linked_fields(form_config, data_source_name):
        """
        Get all fields linked to a specific data source.

        Args:
            form_config (dict): Complete form configuration
            data_source_name (str): Name of the data source

        Returns:
            dict: Field names mapped to their data_source_key
        """
        # Extract fields from config (handle both formats)
        fields = form_config.get('fields', form_config)

        linked = {}
        for field_name, field_config in fields.items():
            if not isinstance(field_config, dict):
                continue

            if field_config.get('data_source') == data_source_name:
                key = field_config.get('data_source_key')
                if key:
                    linked[field_name] = key

        return linked

    @staticmethod
    def get_data_source_item_by_value(source_items, key, value):
        """
        Find a data source item by a specific key-value pair.

        Args:
            source_items (list): List of data source items
            key (str): Key to match
            value: Value to match

        Returns:
            dict: Matching item or None if not found
        """
        for item in source_items:
            if item.get(key) == value:
                return item
        return None

    @staticmethod
    def build_linked_fields_map(form_config):
        """
        Build a complete map of data sources and their linked fields.
        Groups fields by both data source AND section to support multiple
        independent field groups using the same data source.

        Used for frontend JavaScript initialization.

        Args:
            form_config (dict): Complete form configuration

        Returns:
            dict: Map of data sources with field linkages, grouped by section
        """
        data_sources = form_config.get('data_sources', {})
        if not data_sources:
            return {}

        # Extract fields from config (handle both formats)
        fields = form_config.get('fields', form_config)

        # Group fields by data source AND section
        groups = {}  # Key: "datasource_section", Value: {fields: {}, section: ""}

        for field_name, field_config in fields.items():
            if not isinstance(field_config, dict):
                continue

            source_name = field_config.get('data_source')
            if not source_name or source_name not in data_sources:
                continue

            source_key = field_config.get('data_source_key')
            if not source_key:
                continue

            # Get section (defaults to 'default' for fields without section)
            section = field_config.get('section', 'default')

            # Create unique group key combining data source and section
            group_key = f"{source_name}_{section}"

            # Initialize group if not exists
            if group_key not in groups:
                groups[group_key] = {
                    'fields': {},
                    'data': data_sources[source_name],
                    'section': section,
                    'data_source': source_name
                }

            # Add field to group
            groups[group_key]['fields'][field_name] = source_key

        return groups