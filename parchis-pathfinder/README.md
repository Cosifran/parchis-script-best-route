# Parchís Pathfinder

Herramienta de cálculo de movimientos óptimos para el juego Parchís/Ludo, utilizando visión artificial y heurísticas de puntuación.

## Características

- **Captura de pantalla via ADB**: Conexión al emulador Android
- **Detección de tablero con OpenCV**: Identificación de piezas y posiciones mediante segmentación de color HSV
- **Motor de búsqueda de ruta**: Cálculo del movimiento óptimo usando heuristics:
  - +100: Capturar pieza oponente
  - +50: Entrar en zona segura (pasillo o meta)
  - +40: Formar bloqueo (2+ piezas en misma posición)
  - +30: Entrar al tablero desde base (tirada 6)
  - +20: Tirada exacta para llegar a meta
  - -30: Moverse a cuadrado expuesto
  - -20: Romper bloqueo existente
- **Overlay X11**: Visualización del movimiento recomendado en pantalla
- **Herramienta de calibración**: UI interactiva para ajustar colores y posiciones

## Requisitos

- Python 3.8+
- ADB (Android Debug Bridge)
- Emulador Android ejecutándose en localhost:5555
- Librerías del archivo `requirements.txt`

## Instalación

```bash
# Instalar dependencias
cd parchis-pathfinder
pip install -r requirements.txt

# Verificar ADB disponible
adb version
```

## Configuración inicial

1. Inicia tu emulador Android (Andryemu u otro)
2. Asegúrate de que ADB esté conectado:
   ```bash
   adb connect 127.0.0.1:5555
   ```

## Uso

### Capturar pantalla
```bash
python main.py capture
```

### Detectar tablero
```bash
python main.py detect
```

### Calcular mejor movimiento
```bash
python main.py move blue 6
python main.py move red 3
```

### Ejecutar overlay en tiempo real
```bash
python main.py overlay blue
```

### Calibración
```bash
python main.py calibrate
```

## Estructura del proyecto

```
parchis-pathfinder/
├── main.py                 # Punto de entrada CLI
├── requirements.txt        # Dependencias Python
├── src/
│   ├── adb_connector/      # Conexión ADB
│   ├── cv_detector/        # Detección de tablero
│   ├── pathfinder/         # Motor de búsqueda
│   ├── overlay/            # Renderizado overlay
│   └── calibration/        # Herramienta de calibración
├── config/
│   ├── manager.py          # Gestión de configuración
│   ├── settings.yaml       # Ajustes de ejecución
│   └── calibration.yaml   # Valores calibrados
└── tests/
    └── test_pathfinder.py # Tests unitarios
```

## Calibración

La primera vez que uses la herramienta, ejecuta la calibración:

1. `python main.py calibrate`
2. Selecciona las 4 esquinas del tablero haciendo clic
3. Ajusta los rangos HSV para cada color
4. Guarda la calibración

## Configuración

Edita `config/settings.yaml` para ajustar:
- Host/puerto ADB
- Opciones del overlay
- Parámetros de detección

## Troubleshooting

### "ADB not found"
Instala Android SDK platform-tools

### "Connection refused"
Verifica que el emulador esté ejecutándose y que `adb connect 127.0.0.1:5555` funcione

### Overlay no visible
El overlay requiere X11. En Wayland, puede que no funcione correctamente

## Licencia

MIT