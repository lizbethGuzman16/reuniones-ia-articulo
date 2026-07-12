-- Script para insertar 100 tareas de ejemplo en Supabase
-- Ejecuta este script en el SQL Editor de Supabase

-- Primero, vamos a insertar tareas usando datos existentes de reuniones y usuarios
DO $$
DECLARE
    v_reunion_ids uuid[];
    v_correos text[];
    v_reunion_id uuid;
    v_correo text;
    v_estado text;
    v_descripcion text;
    v_dias_offset int;
    i int;
    
    -- Arrays de descripciones realistas
    v_descripciones text[] := ARRAY[
        'Preparar presentación de resultados del Q4',
        'Revisar y aprobar el presupuesto anual',
        'Enviar informe de avances al equipo',
        'Coordinar reunión de seguimiento con stakeholders',
        'Actualizar documentación del proyecto',
        'Implementar feedback recibido en la reunión',
        'Preparar agenda para próxima sesión',
        'Revisar métricas de desempeño del equipo',
        'Contactar a proveedores para cotizaciones',
        'Elaborar plan de acción para próximo trimestre',
        'Validar entregables con el cliente',
        'Organizar capacitación para el equipo',
        'Actualizar cronograma del proyecto',
        'Revisar contratos pendientes',
        'Preparar reporte de gastos',
        'Coordinar con el área de TI la implementación',
        'Realizar seguimiento a tareas pendientes',
        'Documentar decisiones tomadas en la reunión',
        'Enviar minuta de la reunión a participantes',
        'Agendar sesión de retrospectiva',
        'Revisar propuesta de mejora de procesos',
        'Actualizar base de datos de clientes',
        'Preparar demo del producto para cliente',
        'Revisar y optimizar flujo de trabajo',
        'Contactar a recursos humanos por nuevas contrataciones',
        'Elaborar presentación para junta directiva',
        'Validar requisitos técnicos del proyecto',
        'Coordinar pruebas de calidad',
        'Revisar políticas de seguridad',
        'Actualizar manual de procedimientos',
        'Preparar informe de riesgos',
        'Coordinar con equipo de marketing campaña',
        'Revisar análisis de competencia',
        'Elaborar plan de comunicación interna',
        'Validar cumplimiento de normativas',
        'Preparar material de capacitación',
        'Revisar indicadores clave de rendimiento',
        'Coordinar logística para evento',
        'Actualizar plan de contingencia',
        'Revisar feedback de clientes',
        'Elaborar propuesta comercial',
        'Validar especificaciones técnicas',
        'Preparar reporte de ventas mensual',
        'Coordinar con finanzas cierre de mes',
        'Revisar inventario de recursos',
        'Actualizar matriz de riesgos',
        'Preparar análisis de viabilidad',
        'Coordinar sesión de brainstorming',
        'Revisar acuerdos de nivel de servicio',
        'Elaborar plan de mejora continua',
        'Validar entregables del sprint',
        'Preparar documentación para auditoría',
        'Coordinar con legal revisión de contratos',
        'Revisar propuesta de arquitectura',
        'Actualizar roadmap del producto',
        'Preparar presentación de caso de negocio',
        'Coordinar migración de datos',
        'Revisar políticas de privacidad',
        'Elaborar plan de gestión de cambios',
        'Validar requisitos de usuario',
        'Preparar informe de lecciones aprendidas',
        'Coordinar con soporte técnico incidencias',
        'Revisar métricas de satisfacción',
        'Actualizar catálogo de servicios',
        'Preparar análisis de costo-beneficio',
        'Coordinar pruebas de aceptación',
        'Revisar plan de capacidad',
        'Elaborar estrategia de retención',
        'Validar diseño de interfaz',
        'Preparar reporte de incidentes',
        'Coordinar con operaciones implementación',
        'Revisar acuerdos de confidencialidad',
        'Actualizar procedimientos de emergencia',
        'Preparar presentación de resultados',
        'Coordinar sesión de planificación',
        'Revisar propuesta de innovación',
        'Elaborar plan de sucesión',
        'Validar configuración de sistemas',
        'Preparar documentación de API',
        'Coordinar con calidad revisión de procesos',
        'Revisar políticas de uso aceptable',
        'Actualizar guía de estilo',
        'Preparar análisis de tendencias',
        'Coordinar migración a la nube',
        'Revisar plan de recuperación',
        'Elaborar estrategia de crecimiento',
        'Validar cumplimiento de SLA',
        'Preparar reporte de sostenibilidad',
        'Coordinar con compras adquisiciones',
        'Revisar métricas de productividad',
        'Actualizar plan de comunicación de crisis',
        'Preparar presentación de innovación',
        'Coordinar sesión de design thinking',
        'Revisar propuesta de automatización',
        'Elaborar plan de transformación digital',
        'Validar arquitectura de solución',
        'Preparar informe de gobierno corporativo',
        'Coordinar con compliance revisión de políticas',
        'Revisar estrategia de experiencia de cliente'
    ];
    
BEGIN
    -- Obtener IDs de reuniones existentes
    SELECT ARRAY_AGG(id) INTO v_reunion_ids FROM reuniones LIMIT 50;
    
    -- Obtener correos de usuarios existentes
    SELECT ARRAY_AGG(correo) INTO v_correos FROM usuarios;
    
    -- Si no hay reuniones o usuarios, salir
    IF v_reunion_ids IS NULL OR array_length(v_reunion_ids, 1) = 0 THEN
        RAISE NOTICE 'No hay reuniones en la base de datos. Crea reuniones primero.';
        RETURN;
    END IF;
    
    IF v_correos IS NULL OR array_length(v_correos, 1) = 0 THEN
        RAISE NOTICE 'No hay usuarios en la base de datos. Crea usuarios primero.';
        RETURN;
    END IF;
    
    -- Insertar 100 tareas
    FOR i IN 1..100 LOOP
        -- Seleccionar reunión aleatoria
        v_reunion_id := v_reunion_ids[1 + floor(random() * array_length(v_reunion_ids, 1))::int];
        
        -- Seleccionar correo aleatorio (80% asignado, 20% sin asignar)
        IF random() < 0.8 THEN
            v_correo := v_correos[1 + floor(random() * array_length(v_correos, 1))::int];
        ELSE
            v_correo := NULL;
        END IF;
        
        -- Seleccionar estado aleatorio (40% pendiente, 30% en_progreso, 30% completada)
        CASE 
            WHEN random() < 0.4 THEN v_estado := 'pendiente';
            WHEN random() < 0.7 THEN v_estado := 'en_progreso';
            ELSE v_estado := 'completada';
        END CASE;
        
        -- Seleccionar descripción aleatoria
        v_descripcion := v_descripciones[1 + floor(random() * array_length(v_descripciones, 1))::int];
        
        -- Calcular offset de días para fecha de vencimiento
        -- 20% vencidas (pasado), 50% próximas (0-30 días), 30% futuras (30-90 días)
        CASE
            WHEN random() < 0.2 THEN v_dias_offset := -floor(random() * 30)::int; -- Vencidas
            WHEN random() < 0.7 THEN v_dias_offset := floor(random() * 30)::int;  -- Próximas
            ELSE v_dias_offset := 30 + floor(random() * 60)::int;                 -- Futuras
        END CASE;
        
        -- Insertar tarea
        INSERT INTO tareas (
            reunion_id,
            descripcion,
            asignado_a_correo,
            estado,
            fecha_vencimiento,
            fecha_creacion
        ) VALUES (
            v_reunion_id,
            v_descripcion,
            v_correo,
            v_estado,
            CURRENT_DATE + (v_dias_offset || ' days')::interval,
            NOW() - (floor(random() * 60)::int || ' days')::interval -- Creadas en los últimos 60 días
        );
        
    END LOOP;
    
    RAISE NOTICE 'Se insertaron 100 tareas exitosamente';
END $$;

-- Verificar las tareas insertadas
SELECT 
    COUNT(*) as total_tareas,
    COUNT(CASE WHEN estado = 'pendiente' THEN 1 END) as pendientes,
    COUNT(CASE WHEN estado = 'en_progreso' THEN 1 END) as en_progreso,
    COUNT(CASE WHEN estado = 'completada' THEN 1 END) as completadas,
    COUNT(CASE WHEN fecha_vencimiento < CURRENT_DATE AND estado != 'completada' THEN 1 END) as atrasadas,
    COUNT(CASE WHEN asignado_a_correo IS NOT NULL THEN 1 END) as asignadas
FROM tareas;
