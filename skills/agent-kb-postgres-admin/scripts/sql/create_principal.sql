SELECT *
FROM auth.create_account_with_login(
  {{principal_type}}::auth.principal_type,
  {{display_name}},
  {{login_role}},
  {{new_password}},
  {{global_role}}::auth.global_role
);
