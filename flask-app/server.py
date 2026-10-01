import PIL
import os
from flask import Flask, request
import tensorflow as tf
import numpy as np
from keras.preprocessing import image

os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

app = Flask(__name__)


@app.route('/disease-analyzer', methods=['POST'])
def diseaseanalyzer():
    try:
        img_path = request.json['img']

        img_arr = image.img_to_array(
            image.load_img(img_path, color_mode='rgb'))

        img_arr = tf.expand_dims(img_arr, axis=0)

        model = tf.saved_model.load('model')
        f = model.signatures["serving_default"]

        outputs = f(tf.constant(img_arr, tf.float32))

        prediction = tf.math.argmax(outputs["dense"], 1)

        disease = np.array_str(prediction.numpy())

        disease_class = "N/A"

        if disease == '[0]':
            disease_class = 'Blight'
        elif disease == '[1]':
            disease_class = 'Common Rust'
        elif disease == '[2]':
            disease_class = 'Gray Leaf Spot'
        elif disease == '[3]':
            disease_class = 'Healthy'

        return disease_class

    except Exception as e:
        print(str(e))
        return "Prediction Error"


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=4040)
