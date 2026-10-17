-- Somente leitura no PostgreSQL. Salve a célula JSON retornada em contexto-sql.json.
-- Não inventa cidades/coordenadas, não altera cadastros e não depende de tabelas Gold.
-- Um responsável por dispositivo: menor user_id vinculado ao imóvel, deterministicamente.
-- Prefira selecionar imóveis com um só titular se desejar metas estritamente individuais.
SELECT jsonb_pretty(jsonb_build_object(
  'exported_at', CURRENT_TIMESTAMP,
  'devices', COALESCE(jsonb_agg(to_jsonb(contexto) ORDER BY device_id), '[]'::jsonb)
)) AS contexto_json
FROM (
  SELECT d.device_id, vinculo.user_id, p.id AS property_id,
         a.region_id, r.name AS region_name, a.city, a.state,
         pc.group_name AS classification_group, a.latitude::float8, a.longitude::float8,
         d.installation_date, vinculo.association_date
  FROM public.tb_device d
  JOIN public.tb_property p ON p.id=d.property_id
  JOIN public.tb_address a ON a.id=p.address_id
  JOIN public.tb_region r ON r.id=a.region_id
  JOIN public.tb_property_classification pc ON pc.id=p.classification_id
  JOIN LATERAL (
    SELECT up.user_id,up.association_date FROM public.tb_user_property up
    WHERE up.property_id=p.id ORDER BY up.user_id LIMIT 1
  ) vinculo ON true
  WHERE upper(trim(a.state))='SP'
  ORDER BY d.device_id
) contexto;
