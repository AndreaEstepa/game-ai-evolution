# Silksong capture and ROS 2 publisher

Este repositorio contiene una solución para capturar una región de la pantalla, procesar la imagen y publicar el resultado como un topic de ROS 2. La lógica se desarrolló primero en scripts de prueba y luego se integró en un paquete ROS 2 final llamado `silksong_capture`.

## Visión general

La arquitectura del proyecto tiene dos capas:

1. Prototipos de desarrollo en la carpeta [scripts](scripts)
2. Implementación final en el paquete ROS 2 [src/silksong_capture](src/silksong_capture)

La idea principal es la misma en ambos casos:

- capturar una ventana o una zona del monitor con `mss`
- convertir la imagen a un formato útil para OpenCV
- reducir resolución y aplicar filtros
- detectar elementos relevantes (por ejemplo, rojo) o contornos
- publicar la máscara resultante como un mensaje de imagen en ROS 2

## Estructura del proyecto

```text
silksong_ws/
├── README.md
├── config.json
├── scripts/
│   ├── capture_test.py
│   ├── image_processor.py
│   └── processor_test.py
├── src/
│   └── silksong_capture/
│       ├── config/
│       │   └── config.json
│       ├── silksong_capture/
│       │   ├── __init__.py
│       │   ├── image_processor.py
│       │   └── screen_publisher.py
│       ├── package.xml
│       ├── setup.py
│       └── test/
└── build/
```

## Configuración general

La configuración del sistema está en [config.json](config.json) y también se replica en [src/silksong_capture/config/config.json](src/silksong_capture/config/config.json).

Dentro de la configuración se define:

- `monitor`: qué monitor de Windows/Linux se desea capturar
- `region`: rectángulo de la pantalla a observar
- `fps_limit`: límite de fotogramas por segundo
- `vision`: parámetros de OpenCV y detección de rojo

Ejemplo de parámetros relevantes:

- resolución reducida: 320x180
- umbral adaptativo: activado
- `blur`: 3
- `canny_low`: 80
- `canny_high`: 130
- `min_area`: 5
- `red_detection`: hue/valor mínimo para detectar rojo

Esto permite ajustar la sensibilidad de la detección sin cambiar el código.

## Scripts de desarrollo

### 1) [scripts/image_processor.py](scripts/image_processor.py)

Es el núcleo funcional del procesamiento de imagen. Aquí se encuentran las funciones:

- `reduce_resolution(frame, config)`
- `process_image(frame, config)`
- `detect_red(frame, config)`

Estas funciones convierten la imagen a escala de grises, reducen resolución, aplican desenfoque gaussiano, umbral adaptativo o fijo, obtienen bordes con Canny y generan una máscara de contornos. La detección de rojo usa HSV y filtra por rango de saturación y valor.

La lógica de este archivo es la base de la implementación final; el archivo dentro del paquete ROS 2 [src/silksong_capture/silksong_capture/image_processor.py](src/silksong_capture/silksong_capture/image_processor.py) es esencialmente la misma funcionalidad preparada para ser importada por el nodo ROS.

### 2) [scripts/capture_test.py](scripts/capture_test.py)

Este script es una prueba de captura directa de pantalla. Su objetivo es verificar que el monitor y la región definidos funcionen correctamente. Hace lo siguiente:

- carga la configuración desde [config.json](config.json)
- abre un `MSS()` para obtener la captura del monitor seleccionado
- ajusta la región sumando los offsets del monitor
- convierte la imagen a `BGR`
- muestra la imagen en una ventana OpenCV
- controla el framerate con `time.time()` y `cv2.waitKey()`

Es una comprobación visual sobre si la región capturada es la correcta antes de integrarla en ROS.

### 3) [scripts/processor_test.py](scripts/processor_test.py)

Es la prueba que consolida la captura + el preprocesado. Aquí se usa la lógica de [scripts/image_processor.py](scripts/image_processor.py) para:

- procesar cada frame con `process_image()`
- mostrar imágenes de salida: original, binaria, bordes, gris y máscara roja
- combinar la detección roja con los bordes para visualizar la respuesta final

En otras palabras, este archivo es el puente entre la prueba de captura y la versión final del nodo ROS, porque demuestra que la imagen procesada es útil para detección y visualización antes de publicarla en un topic.

## Implementación final: nodo ROS 2

### [src/silksong_capture/silksong_capture/screen_publisher.py](src/silksong_capture/silksong_capture/screen_publisher.py)

Este es el punto clave del proyecto. La clase `ScreenPublisher(Node)` se encarga de:

- inicializar el nodo ROS con nombre `screen_publisher`
- cargar configuración desde [src/silksong_capture/config/config.json](src/silksong_capture/config/config.json)
- crear un publicador del tipo `sensor_msgs/Image` sobre el topic `/vision/red_mask`
- usar un temporizador para ejecutar la captura y publicación a una frecuencia definida por `fps_limit`
- capturar la región definida con `MSS`
- transformar la imagen a BGR
- procesarla usando `detect_red()` y `process_image()`
- combinar `red_mask` con `edges`
- convertir el resultado a un mensaje OpenCV con `CvBridge`
- publicar el mensaje en ROS 2

El flujo real es:

```text
config.json
   ↓
MSS captura region
   ↓
OpenCV BGR conversion
   ↓
detect_red() + process_image()
   ↓
bitwise_or(mask, edges)
   ↓
CvBridge -> Image msg
   ↓
/vision/red_mask
```

### [src/silksong_capture/silksong_capture/image_processor.py](src/silksong_capture/silksong_capture/image_processor.py)

Este archivo es la versión del mismo módulo de procesamiento usado por el nodo final. No es un archivo independiente del proyecto; es la implementación integrada de la lógica desarrollada en [scripts/image_processor.py](scripts/image_processor.py).

Por tanto, la relación es:

- [scripts/image_processor.py](scripts/image_processor.py): versión original / prototipo
- [src/silksong_capture/silksong_capture/image_processor.py](src/silksong_capture/silksong_capture/image_processor.py): versión reutilizada y enlazada desde el nodo ROS

El archivo final `screen_publisher.py` importa exactamente estas funciones:

```python
from .image_processor import process_image, detect_red
```

## Package ROS 2

La estructura del paquete se define en:

- [src/silksong_capture/setup.py](src/silksong_capture/setup.py)
- [src/silksong_capture/package.xml](src/silksong_capture/package.xml)

Aquí se registran:

- el nombre del paquete: `silksong_capture`
- la dependencia de `rclpy`, `sensor_msgs`, `cv_bridge`, `ament_index_python`
- el entry point `screen_publisher = silksong_capture.screen_publisher:main`

Esto permite ejecutar el nodo como un executable de ROS 2 con un comando como:

```bash
ros2 run silksong_capture screen_publisher
```

## Relación entre pruebas y implementación final

El desarrollo del proyecto sigue este patrón:

- [scripts/capture_test.py](scripts/capture_test.py): validación del acceso a la captura de pantalla
- [scripts/processor_test.py](scripts/processor_test.py): validación del preprocesado y la detección visual
- [scripts/image_processor.py](scripts/image_processor.py): funciones reutilizables de transformación y detección
- [src/silksong_capture/silksong_capture/screen_publisher.py](src/silksong_capture/silksong_capture/screen_publisher.py): integración final en ROS 2 con publicación de topic

La implementación final es, por tanto, una evolución de lo que se probó en los scripts: la misma lógica de visión, pero encapsulada en un nodo de ROS 2 que publica en `/vision/red_mask`.

## Cómo lanzar y probar el proyecto

### 1) Ejecutar los scripts de prueba con Python 3

Los prototipos de desarrollo se pueden ejecutar directamente desde la raíz del proyecto usando Python 3. Si existe un entorno virtual del proyecto, primero se activa:

```bash
cd /media/pegaso/4C22A6E222A6D06E2/I.Computadores/Robótica/silksong_ws
source .venv/bin/activate
python3 scripts/capture_test.py
```

Y para la prueba de procesamiento:

```bash
cd /media/pegaso/4C22A6E222A6D06E2/I.Computadores/Robótica/silksong_ws
source .venv/bin/activate
python3 scripts/processor_test.py
```

Si además quieres ejecutar pruebas unitarias o de validación con Python, se puede lanzar desde el paquete o desde la carpeta del proyecto usando `pytest`:

```bash
cd /media/pegaso/4C22A6E222A6D06E2/I.Computadores/Robótica/silksong_ws
source .venv/bin/activate
python3 -m pytest
```

En este repositorio, la lógica de visualización y detección se ha validado de manera manual con estos scripts antes de integrarlo en ROS 2.

### 2) Activar el entorno virtual y ejecutar el proyecto

La práctica recomendada es entrar al entorno virtual antes de lanzar cualquiera de los scripts o pruebas:

```bash
cd /media/pegaso/4C22A6E222A6D06E2/I.Computadores/Robótica/silksong_ws
source .venv/bin/activate
```

Una vez activo, puedes ejecutar cualquiera de los prototipos manualmente con `python3` como se mostró antes.

### 3) Lanzar la versión final con ROS 2

La implementación final se ejecuta como un nodo ROS 2 del paquete `silksong_capture`.

Primero se compila el workspace si hace falta:

```bash
cd /media/pegaso/4C22A6E222A6D06E2/I.Computadores/Robótica/silksong_ws
source /opt/ros/<distro>/setup.bash
colcon build
source install/setup.bash
```

Y después se lanza el publicador:

```bash
ros2 run silksong_capture screen_publisher
```

Esto empezará a capturar la región configurada, procesar la imagen y publicar el resultado en el topic:

```text
/vision/red_mask
```

### 4) Ver la imagen publicada con `rqt_image_view`

Para visualizar la imagen publicada por el topic, se abre otra terminal y se ejecuta:

```bash
source /opt/ros/<distro>/setup.bash
ros2 run rqt_image_view rqt_image_view
```

Entonces, en la interfaz de `rqt_image_view`:

- selecciona el topic `/vision/red_mask`
- se mostrará la imagen procesada publicada por el nodo `screen_publisher`

Esto permite comprobar visualmente que la captura, la binarización y la detección de rojo están funcionando correctamente en tiempo real.

## Resumen

El proyecto es una arquitectura de visión por computador aplicada a una captura de pantalla. Comienza con pruebas artesanales en Python para validar la captura y la detección, y termina con un nodo ROS 2 que publica la máscara detectada para que otros nodos la consuman.

Los archivos clave son:

- [scripts/capture_test.py](scripts/capture_test.py)
- [scripts/processor_test.py](scripts/processor_test.py)
- [scripts/image_processor.py](scripts/image_processor.py)
- [src/silksong_capture/silksong_capture/image_processor.py](src/silksong_capture/silksong_capture/image_processor.py)
- [src/silksong_capture/silksong_capture/screen_publisher.py](src/silksong_capture/silksong_capture/screen_publisher.py)
- [src/silksong_capture/config/config.json](src/silksong_capture/config/config.json)

Si se quiere entender el proyecto completo, el orden recomendado es:

1. leer la configuración
2. revisar el procesamiento de imagen
3. estudiar los tests de desarrollo
4. terminar en el publicador ROS 2 final
