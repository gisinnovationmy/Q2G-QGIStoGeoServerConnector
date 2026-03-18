"""
PostGIS Credentials Management Module - SIMPLIFIED

This module provides simple, reliable PostGIS credential storage.
Credentials are saved to postgis.ini in the plugin directory.
"""

import os
import configparser


class PostGISCredentialsManager:
    """Simple manager for PostGIS credentials."""
    
    def __init__(self, config_filename="postgis.ini"):
        """Initialize the credentials manager."""
        self.config_filename = config_filename
        self.config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            config_filename
        )
    
    def _create_section_name(self, pg_params):
        """Create unique section name: PostGIS_database_host_port"""
        port = str(pg_params['port'])
        section = f"PostGIS_{pg_params['database']}_{pg_params['host']}_{port}"
        return section.replace('.', '_').replace('-', '_')
    
    def save_credentials(self, pg_params, log_callback=None):
        """
        Save credentials to postgis.ini file.
        
        Args:
            pg_params: dict with keys: host, port, database, user, passwd, schema
            log_callback: optional function for logging
            
        Returns:
            bool: True if saved successfully
        """
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Load existing config
            config = configparser.ConfigParser()
            if os.path.exists(self.config_path):
                config.read(self.config_path)
            
            # Create section
            section_name = self._create_section_name(pg_params)
            config[section_name] = {
                "host": pg_params.get('host', ''),
                "port": str(pg_params.get('port', '')),
                "database": pg_params.get('database', ''),
                "user": pg_params.get('user', ''),
                "passwd": pg_params.get('passwd', ''),
                "schema": pg_params.get('schema', 'public'),
                "table": pg_params.get('table', '')
            }
            
            # Write to file
            with open(self.config_path, "w") as f:
                config.write(f)
            
            if log_callback:
                log_callback(f"✓ Credentials saved: {pg_params['database']}@{pg_params['host']}")
            
            return True
            
        except Exception as e:
            if log_callback:
                log_callback(f"✗ Failed to save: {str(e)}")
            return False
    
    def load_credentials(self, database, host, port, log_callback=None):
        """Load credentials from postgis.ini file."""
        try:
            if not os.path.exists(self.config_path):
                return None
            
            config = configparser.ConfigParser()
            config.read(self.config_path)
            
            pg_params = {'database': database, 'host': host, 'port': port}
            section_name = self._create_section_name(pg_params)
            
            if section_name not in config:
                return None
            
            section = config[section_name]
            return {
                'host': section.get('host', ''),
                'port': section.get('port', ''),
                'database': section.get('database', ''),
                'user': section.get('user', ''),
                'passwd': section.get('passwd', ''),
                'schema': section.get('schema', 'public'),
                'table': section.get('table', '')
            }
            
        except Exception:
            return None
    
    def list_saved_connections(self, log_callback=None):
        """List all saved PostGIS connections."""
        try:
            if not os.path.exists(self.config_path):
                return []
            
            config = configparser.ConfigParser()
            config.read(self.config_path)
            
            connections = []
            for section_name in config.sections():
                if section_name.startswith('PostGIS_'):
                    section = config[section_name]
                    connections.append({
                        'section_name': section_name,
                        'host': section.get('host', ''),
                        'port': section.get('port', ''),
                        'database': section.get('database', ''),
                        'user': section.get('user', ''),
                        'passwd': section.get('passwd', ''),
                        'schema': section.get('schema', 'public')
                    })
            
            return connections
            
        except Exception:
            return []
    
    def delete_credentials(self, database, host, port, log_callback=None):
        """Delete credentials from postgis.ini file."""
        try:
            if not os.path.exists(self.config_path):
                return False
            
            config = configparser.ConfigParser()
            config.read(self.config_path)
            
            pg_params = {'database': database, 'host': host, 'port': port}
            section_name = self._create_section_name(pg_params)
            
            if section_name not in config:
                return False
            
            config.remove_section(section_name)
            
            with open(self.config_path, "w") as f:
                config.write(f)
            
            if log_callback:
                log_callback(f"✓ Deleted: {database}@{host}:{port}")
            
            return True
            
        except Exception as e:
            if log_callback:
                log_callback(f"✗ Delete failed: {str(e)}")
            return False
