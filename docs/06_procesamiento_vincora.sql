-- VINCORA: persistencia verificable de grabaciones y resultados.
-- Idempotente y compatible con las tablas existentes usuarios/reuniones/participantes/tareas/resumenes.

create extension if not exists pgcrypto;

create table if not exists procesamientos_reunion (
  id uuid primary key default gen_random_uuid(),
  reunion_id uuid not null unique references reuniones(id) on delete cascade,
  estado text not null default 'pendiente'
    check (estado in ('pendiente','transcribiendo','analizando','procesando','completado','error')),
  progreso integer not null default 0 check (progreso between 0 and 100),
  detalle jsonb not null default '{}'::jsonb,
  palabras integer not null default 0,
  iniciado_en timestamptz not null default now(),
  actualizado_en timestamptz not null default now(),
  completado_en timestamptz
);

create table if not exists grabaciones (
  id uuid primary key default gen_random_uuid(),
  reunion_id uuid not null references reuniones(id) on delete cascade,
  egress_id text not null unique,
  tipo text not null check (tipo in ('reunion','participante')),
  participante_identity text,
  participante_nombre text,
  ruta_objeto text not null,
  estado text not null default 'iniciada'
    check (estado in ('iniciada','activa','completada','error','abortada')),
  error text,
  creado_en timestamptz not null default now(),
  actualizado_en timestamptz not null default now()
);

create unique index if not exists grabaciones_reunion_general_unica
  on grabaciones(reunion_id, tipo) where tipo = 'reunion';
create unique index if not exists grabaciones_participante_unica
  on grabaciones(reunion_id, participante_identity) where tipo = 'participante';

create table if not exists segmentos_reunion (
  id uuid primary key,
  reunion_id uuid not null references reuniones(id) on delete cascade,
  procesamiento_id uuid references procesamientos_reunion(id) on delete set null,
  hablante text not null default 'No especificado',
  texto text not null check (length(trim(texto)) > 0),
  inicio_segundos numeric(12,3) not null default 0 check (inicio_segundos >= 0),
  fin_segundos numeric(12,3) not null default 0 check (fin_segundos >= inicio_segundos),
  origen text,
  creado_en timestamptz not null default now()
);

create table if not exists informes_reunion (
  id uuid primary key default gen_random_uuid(),
  reunion_id uuid not null unique references reuniones(id) on delete cascade,
  procesamiento_id uuid references procesamientos_reunion(id) on delete set null,
  estado text not null default 'borrador'
    check (estado in ('generando','borrador','aprobado','rechazado')),
  resumen text not null default '',
  contenido jsonb not null default '{}'::jsonb,
  modelo text not null default '',
  creado_en timestamptz not null default now(),
  actualizado_en timestamptz not null default now()
);

create table if not exists temas_tratados (
  id uuid primary key default gen_random_uuid(),
  informe_id uuid not null references informes_reunion(id) on delete cascade,
  descripcion text not null,
  evidencias jsonb not null check (jsonb_array_length(evidencias) > 0),
  estado text not null default 'detectado' check (estado in ('detectado','confirmado','rechazado'))
);

create table if not exists acuerdos (
  id uuid primary key default gen_random_uuid(),
  informe_id uuid not null references informes_reunion(id) on delete cascade,
  descripcion text not null,
  responsable text not null default 'No especificado',
  fecha_limite text not null default 'No especificado',
  evidencias jsonb not null check (jsonb_array_length(evidencias) > 0),
  estado text not null default 'detectado' check (estado in ('detectado','confirmado','rechazado'))
);

create table if not exists tareas_detectadas (
  id uuid primary key default gen_random_uuid(),
  informe_id uuid not null references informes_reunion(id) on delete cascade,
  descripcion text not null,
  responsable text not null default 'No especificado',
  fecha_limite text not null default 'No especificado',
  evidencias jsonb not null check (jsonb_array_length(evidencias) > 0),
  estado text not null default 'detectado' check (estado in ('detectado','confirmado','rechazado'))
);

create table if not exists decisiones (
  id uuid primary key default gen_random_uuid(),
  informe_id uuid not null references informes_reunion(id) on delete cascade,
  descripcion text not null,
  evidencias jsonb not null check (jsonb_array_length(evidencias) > 0),
  estado text not null default 'detectado' check (estado in ('detectado','confirmado','rechazado'))
);

create table if not exists versiones_informe (
  id uuid primary key default gen_random_uuid(),
  informe_id uuid not null references informes_reunion(id) on delete cascade,
  numero integer not null check (numero > 0),
  contenido jsonb not null,
  creado_por uuid references usuarios(id) on delete set null,
  creado_en timestamptz not null default now(),
  unique (informe_id, numero)
);

create table if not exists aprobaciones_informe (
  id uuid primary key default gen_random_uuid(),
  informe_id uuid not null references informes_reunion(id) on delete cascade,
  usuario_id uuid references usuarios(id) on delete set null,
  estado text not null check (estado in ('aprobado','rechazado')),
  comentario text,
  creado_en timestamptz not null default now()
);

create index if not exists grabaciones_reunion_idx on grabaciones(reunion_id, estado);
create index if not exists segmentos_reunion_tiempo_idx on segmentos_reunion(reunion_id, inicio_segundos);
create index if not exists elementos_informe_acuerdos_idx on acuerdos(informe_id);
create index if not exists elementos_informe_tareas_idx on tareas_detectadas(informe_id);
create index if not exists elementos_informe_decisiones_idx on decisiones(informe_id);

alter table procesamientos_reunion enable row level security;
alter table grabaciones enable row level security;
alter table segmentos_reunion enable row level security;
alter table informes_reunion enable row level security;
alter table temas_tratados enable row level security;
alter table acuerdos enable row level security;
alter table tareas_detectadas enable row level security;
alter table decisiones enable row level security;
alter table versiones_informe enable row level security;
alter table aprobaciones_informe enable row level security;

-- No se crean políticas públicas: estas tablas se escriben desde la API con service_role.
