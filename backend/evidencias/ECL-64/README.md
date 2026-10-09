# Evidencia ECL-64 / ST-038

Consultar [VALIDACION_ST038.md](../../VALIDACION_ST038.md).

comparacion.json contiene SQL real, parámetros sintéticos, versiones,
resultados funcionales y 80 planes antes/después. La comparación utiliza la
misma base de ST-037 y alterna el orden de ejecución. No representa latencia HTTP.

La reducción de 58 a 1 byte es la suma de pg_column_size de los valores internos,
sin protocolo ni cabeceras: no representa tráfico de red o tamaño del dashboard.
No se demuestra aceleración; la mejora es recuperar solamente un booleano.

verificacion.json registra resultados observados de pruebas y hashes de fuentes
y evidencia. No es una ejecución de CI ni una aprobación humana.

Para repetir, configurar privadamente DATABASE_URL de la base sintética
ecologistica_ecl63_queries_test y ejecutar desde backend:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python scripts/compare_client_lookup.py --output evidencias/ECL-64-repeticion
```

No publicar la URL ni secretos. La herramienta rechaza otro nombre de base.
La medición es de solo lectura y no crea índices o datos. Usar otra carpeta de
salida para conservar las mediciones originales. La semilla se prepara con las
instrucciones de [ST-037](../ECL-63/README.md).

Dashboard/rutas y comparación del límite de 250 KB siguen pendientes.
