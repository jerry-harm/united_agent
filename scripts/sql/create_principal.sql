DO $$
BEGIN
  IF app.current_business_role() = 'admin'::app.business_role
     AND {{business_role}} <> 'normal_user' THEN
    RAISE EXCEPTION 'policy violation: admin may create only normal_user principals';
  ELSIF app.current_business_role() = 'super_admin'::app.business_role
     AND {{business_role}} NOT IN ('normal_user', 'admin') THEN
    RAISE EXCEPTION 'policy violation: super_admin may create only normal_user or admin principals';
  ELSIF app.current_business_role() NOT IN ('admin'::app.business_role, 'super_admin'::app.business_role) THEN
    RAISE EXCEPTION 'policy violation: only admin or super_admin may create principals';
  END IF;
END
$$;

SELECT * FROM app.bootstrap_principal(
  {{principal_type}},
  {{display_name}},
  {{business_role}},
  {{login_role}},
  {{new_password}}
);
