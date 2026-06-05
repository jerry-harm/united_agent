SELECT *
FROM auth.revoke_global_role(
  {{account_id}}::bigint,
  {{role_name}}::auth.global_role
);
