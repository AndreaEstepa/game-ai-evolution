# Silksong: percepción y aprendizaje evolutivo

Este workspace contiene la base de un proyecto para que un agente de inteligencia artificial juegue una sección delimitada del mapa de *Hollow Knight: Silksong*. La idea es conectar la percepción visual del juego con una política neuronal entrenada mediante un algoritmo evolutivo EDNN.

> **Estado actual:** está implementada la captura de pantalla, un preprocesado básico de imagen y la publicación de una máscara visual como tópico ROS 2. La red neuronal, el algoritmo evolutivo, la evaluación del progreso y el envío de controles al juego todavía no están implementados. Por tanto, el nodo actual observa la pantalla, pero no juega.

## Objetivo y arquitectura prevista

El objetivo es entrenar y evaluar un agente en una sección concreta del mapa, empezando por un recorrido o tarea acotados. El flujo previsto es:

```text
Pantalla del juego
       ↓
Captura y preprocesado visual (implementados)
       ↓
Observación para el agente
       ↓
Política neuronal EDNN (pendiente)
       ↓
Acción de juego (pendiente)
       ↓
Evaluación del episodio y fitness (pendiente)
       └──────────────→ siguiente generación
```

En el enfoque evolutivo, cada individuo representa una política neuronal candidata. Se evalúa durante uno o más episodios y se le asigna una puntuación de *fitness*; el algoritmo usa esas puntuaciones para generar la siguiente población. La representación de los individuos, las operaciones evolutivas, las entradas y salidas de la red, y la fórmula de *fitness* se definirán al implementar el entrenador. No se presupone que el agente ya tenga navegación, combate, memoria o detección semántica.

## Qué existe hoy

El paquete ROS 2 `silksong_capture` captura una región de un monitor, la procesa con OpenCV y publica una imagen monocromática en `/vision/red_mask` (`sensor_msgs/msg/Image`). La imagen publicada combina una máscara HSV de píxeles rojos con los bordes detectados; se reduce a `320 × 180` con la configuración actual.

Los scripts de `scripts/` sirven para probar la captura y visualizar el procesamiento sin ROS 2. El nodo ROS 2 integra esa funcionalidad para que otros nodos puedan consumir la imagen. Aún no hay nodo de agente ni flujo de entrenamiento.

## Estructura

```text
silksong_ws/
├── README.md
├── config.json                         # Configuración para los scripts de prueba
├── scripts/
│   ├── capture_test.py                 # Prueba de captura y visualización
│   ├── image_processor.py              # Funciones de preprocesado y detección
│   └── processor_test.py               # Captura y visualiza las salidas del procesador
└── src/
    └── silksong_capture/
        ├── config/config.json          # Configuración instalada con el paquete ROS 2
        ├── silksong_capture/
        │   ├── image_processor.py      # Procesamiento utilizado por el nodo ROS 2
        │   └── screen_publisher.py     # Publicador del tópico de visión
        ├── package.xml
        └── setup.py
```

`build/`, `install/` y `log/` son directorios generados por `colcon`; no contienen el código fuente del proyecto.

## Configuración de captura

Los parámetros están en [config.json](config.json) y en [src/silksong_capture/config/config.json](src/silksong_capture/config/config.json). Los scripts leen el primero y el paquete ROS 2 carga el segundo; hay que mantenerlos sincronizados cuando se cambien los valores.

| Clave | Uso |
|---|---|
| `monitor` | Índice del monitor que se captura. |
| `region` | Rectángulo capturado (`left`, `top`, `width`, `height`), relativo al monitor. |
| `window_name` | Título de ventana usado por los scripts de prueba. |
| `fps_limit` | Frecuencia objetivo de captura/publicación. |
| `vision.resize_width`, `vision.resize_height` | Resolución de procesamiento y publicación. |
| `vision.blur`, `vision.threshold`, `vision.adaptive_threshold` | Parámetros de reducción de ruido y umbralización. |
| `vision.canny_low`, `vision.canny_high`, `vision.min_area` | Parámetros de detección y filtrado de contornos. |
| `vision.red_detection.enabled` | Activa la detección de rojo en los scripts de prueba. |
| `vision.red_detection.saturation_min`, `vision.red_detection.value_min` | Umbrales HSV para la máscara roja. |

La posición de la región depende de la resolución, la disposición de monitores y la ventana del juego. Hay que ajustarla al entorno donde se ejecute.

## Requisitos

- Python 3.
- ROS 2 y `colcon` para compilar y ejecutar el nodo.
- Dependencias de ROS del paquete: `rclpy`, `sensor_msgs`, `cv_bridge` y `ament_index_python`.
- Bibliotecas de Python utilizadas por el código: `mss`, `numpy` y `opencv-python` (`cv2`).

La instalación de ROS 2 y de sus dependencias varía según la distribución y el sistema operativo. Instala también las bibliotecas de Python en el entorno que vaya a ejecutar los scripts y el nodo.

## Ejecutar las pruebas visuales

Desde la raíz de `silksong_ws`, con las dependencias de Python disponibles:

```bash
python3 scripts/capture_test.py
python3 scripts/processor_test.py
```

`capture_test.py` muestra la región capturada. `processor_test.py` muestra ventanas para la imagen original, la imagen binaria, los bordes, la escala de grises y, si está activada, la máscara roja combinada con los bordes. Pulsa `q` para cerrar las ventanas.

## Compilar y ejecutar el publicador ROS 2

En una terminal con el entorno de ROS 2 instalado y configurado:

```bash
cd silksong_ws
source /opt/ros/<distro>/setup.bash
colcon build --packages-select silksong_capture
source install/setup.bash
ros2 run silksong_capture screen_publisher
```

Sustituye `<distro>` por la distribución de ROS 2 instalada. El nodo publica en:

```text
/vision/red_mask
```

Para comprobar el tópico desde otra terminal con ROS 2 configurado:

```bash
ros2 topic list
ros2 run rqt_image_view rqt_image_view
```

En `rqt_image_view`, selecciona `/vision/red_mask`.

## Próximos componentes del agente

1. **Definir una tarea y episodio:** delimitar la sección del mapa, el estado inicial, el objetivo y las condiciones de terminación.
2. **Definir observaciones y acciones:** decidir qué información recibe la red y qué controles discretos o continuos puede emitir.
3. **Implementar la interfaz de control:** conectar las acciones con el juego de forma reproducible y segura para reiniciar episodios.
4. **Implementar EDNN:** especificar la codificación de la red en cada individuo, la población y los operadores evolutivos.
5. **Diseñar el *fitness* y el registro:** medir el desempeño por episodio y guardar generaciones, puntuaciones y mejores individuos.
6. **Evaluar y ajustar:** comparar resultados en condiciones repetibles antes de ampliar la zona o la dificultad.