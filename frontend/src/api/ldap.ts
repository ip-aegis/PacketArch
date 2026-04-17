/**
 * LDAP / Active Directory admin API client
 */

import apiClient from './client';

export interface LdapSettings {
  ldap_enabled: boolean;
  ldap_server_url: string;
  ldap_use_ssl: boolean;
  ldap_start_tls: boolean;
  ldap_verify_ssl: boolean;
  ldap_bind_dn: string;
  ldap_bind_password_set: boolean;
  ldap_search_base: string;
  ldap_user_search_filter: string;
  ldap_email_attribute: string;
  ldap_display_name_attribute: string;
}

export interface LdapSettingsUpdate {
  ldap_enabled?: boolean;
  ldap_server_url?: string;
  ldap_use_ssl?: boolean;
  ldap_start_tls?: boolean;
  ldap_verify_ssl?: boolean;
  ldap_bind_dn?: string;
  ldap_bind_password?: string;
  ldap_search_base?: string;
  ldap_user_search_filter?: string;
  ldap_email_attribute?: string;
  ldap_display_name_attribute?: string;
}

export interface LdapTestConnectionRequest {
  ldap_server_url: string;
  ldap_use_ssl: boolean;
  ldap_start_tls: boolean;
  ldap_verify_ssl: boolean;
  ldap_bind_dn: string;
  ldap_bind_password?: string;
  ldap_search_base?: string;
}

export interface LdapTestConnectionResponse {
  success: boolean;
  message: string;
  server_info: string | null;
}

export const ldapApi = {
  getSettings: async (): Promise<LdapSettings> => {
    const response = await apiClient.get<LdapSettings>('/api/v1/ldap/settings');
    return response.data;
  },

  updateSettings: async (settings: LdapSettingsUpdate): Promise<LdapSettings> => {
    const response = await apiClient.put<LdapSettings>('/api/v1/ldap/settings', settings);
    return response.data;
  },

  testConnection: async (
    request: LdapTestConnectionRequest
  ): Promise<LdapTestConnectionResponse> => {
    const response = await apiClient.post<LdapTestConnectionResponse>(
      '/api/v1/ldap/test-connection',
      request
    );
    return response.data;
  },
};

export default ldapApi;
