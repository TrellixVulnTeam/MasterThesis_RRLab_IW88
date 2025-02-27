from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import hashlib
import io
import logging
import os
import sys

from lxml import etree
import PIL.Image
import tensorflow as tf

from object_detection.utils import dataset_util
from object_detection.utils import label_map_util


def dict_to_tf_example(data,
                       dataset_directory,
                       label_map_dict,
                       ignore_difficult_instances=False,
                       image_subdirectory='JPEGImages'):
  """Convert XML derived dict to tf.Example proto.
  Notice that this function normalizes the bounding box coordinates provided
  by the raw data.
  Args:
    data: dict holding PASCAL XML fields for a single image (obtained by
      running dataset_util.recursive_parse_xml_to_dict)
    dataset_directory: Path to root directory holding PASCAL dataset
    label_map_dict: A map from string label names to integers ids.
    ignore_difficult_instances: Whether to skip difficult instances in the
      dataset  (default: False).
    image_subdirectory: String specifying subdirectory within the
      PASCAL dataset directory holding the actual image data.
  Returns:
    example: The converted tf.Example.
  Raises:
    ValueError: if the image pointed to by data['filename'] is not a valid JPEG

    EXAMPLE
    python tf_record_builder.py ./unreal_60m/UnrealDataset/Mapped480/ Annotations/ unreal_60m/UnrealDataset/Mapped480/unreal2caltech.tfrecord unreal_60m/unreal_label_map.pbtxt 


    
  """
  #img_path = os.path.join(data['folder'], image_subdirectory, data['filename'])
  img_path = os.path.join(image_subdirectory, data['filename'])
  full_path = os.path.join(dataset_directory, img_path)
  with tf.gfile.GFile(full_path, 'rb') as fid:
    encoded_jpg = fid.read()
  encoded_jpg_io = io.BytesIO(encoded_jpg)
  image = PIL.Image.open(encoded_jpg_io)
  if image.format != 'JPEG':
    raise ValueError('Image format not JPEG')
  key = hashlib.sha256(encoded_jpg).hexdigest()

  width = int(data['size']['width'])
  height = int(data['size']['height'])

  xmin = []
  ymin = []
  xmax = []
  ymax = []
  classes = []
  classes_text = []
  truncated = []
  poses = []
  difficult_obj = []
  for obj in data['object']:
    difficult = bool(int(obj['difficult']))
    if ignore_difficult_instances and difficult:
      continue

    difficult_obj.append(int(difficult))

    xmin.append(float(obj['bndbox']['xmin']) / width)
    ymin.append(float(obj['bndbox']['ymin']) / height)
    xmax.append(float(obj['bndbox']['xmax']) / width)
    ymax.append(float(obj['bndbox']['ymax']) / height)
    classes_text.append(obj['name'].encode('utf8'))
    classes.append(label_map_dict[obj['name']])
    truncated.append(int(obj['truncated']))
    poses.append(obj['pose'].encode('utf8'))

  example = tf.train.Example(features=tf.train.Features(feature={
      'image/height': dataset_util.int64_feature(height),
      'image/width': dataset_util.int64_feature(width),
      'image/filename': dataset_util.bytes_feature(
          data['filename'].encode('utf8')),
      'image/source_id': dataset_util.bytes_feature(
          data['filename'].encode('utf8')),
      'image/key/sha256': dataset_util.bytes_feature(key.encode('utf8')),
      'image/encoded': dataset_util.bytes_feature(encoded_jpg),
      'image/format': dataset_util.bytes_feature('jpeg'.encode('utf8')),
      'image/object/bbox/xmin': dataset_util.float_list_feature(xmin),
      'image/object/bbox/xmax': dataset_util.float_list_feature(xmax),
      'image/object/bbox/ymin': dataset_util.float_list_feature(ymin),
      'image/object/bbox/ymax': dataset_util.float_list_feature(ymax),
      'image/object/class/text': dataset_util.bytes_list_feature(classes_text),
      'image/object/class/label': dataset_util.int64_list_feature(classes),
      'image/object/difficult': dataset_util.int64_list_feature(difficult_obj),
      'image/object/truncated': dataset_util.int64_list_feature(truncated),
      'image/object/view': dataset_util.bytes_list_feature(poses),
  }))
  return example

def read_examples_list(path):
    examples = []
    
    with open(path+"examples.txt", "r") as f:
        for line in f:
            examples.append(line[:-1])

    return examples

def main(_):
 
    data_dir = sys.argv[1]
    annotations_dir = sys.argv[2]
    output_path = sys.argv[3]
    label_map_path = sys.argv[4]
  
    writer = tf.python_io.TFRecordWriter(output_path)

    label_map_dict = label_map_util.get_label_map_dict(label_map_path)

    annotations_dir = os.path.join(data_dir, annotations_dir)
    examples_list = read_examples_list(data_dir)
    
    counter = 0
    for idx, example in enumerate(examples_list):
        
        exSplit = example.split(" ")
        
        if int(exSplit[1])  !=  0:
          
            path = os.path.join(annotations_dir, exSplit[0] + '.xml')
            
            with tf.gfile.GFile(path, 'r') as fid:
                xml_str = fid.read()
            
            xml = etree.fromstring(xml_str)
            data = dataset_util.recursive_parse_xml_to_dict(xml)['annotation']
            
            
            img_path = os.path.join(data_dir, 'JPEGImages', data['filename'])
            if os.path.isfile(img_path):
                counter += 1
                print('Files in Tfrecord: ', counter, '->', img_path)
            else:
                continue
            
            
                
            tf_example = dict_to_tf_example(data, data_dir, label_map_dict, False)
            writer.write(tf_example.SerializeToString())

    writer.close()
    
main("")