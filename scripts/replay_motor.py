#!/usr/bin/env python


import rospy
import numpy as np
import keras
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from lstm.msg import Event
from geometry_msgs.msg import Twist
from raspimouse_ros_2.msg import LightSensorValues, ButtonValues, LedValues


def event_callback(eve):
    e = eve
    episode = [e.right_forward, e.right_side, e.left_side, e.left_forward,e.linear_x, e.angular_z]
    episodem = [e.linear_x, e.angular_z]
    global history
    global historym
    history = np.vstack((history, episode))  
    historym = np.vstack((historym, episodem)) 

      
def sensor_callback(messages):
    s = messages
    global sens
    sensor = [s.right_forward, s.right_side, s.left_side, s.left_forward]
    sens = np.vstack((sens, sensor))
    sens = sens[1: 101,]

def button_callback(btn_msg):
    leds = LedValues()
    leds.left_side = btn_msg.front_toggle
    leds.left_forward = btn_msg.mid_toggle
    leds.right_forward = btn_msg.rear_toggle
    led_pub.publish(leds)
    on = btn_msg
    if btn_msg.mid:
        global history
        global model
        step = 1
        size = len (history)
               
        history = history.reshape(1,-1,6)
        sen = history[ : , step : step + 100, ]
        step += 1
        print sen
        for i in range(size - 102):
            temp = history[ : , step : step + 100, ]
            sen = np.vstack((sen, temp))
            step += 1
         
 #       model.add(LSTM(20,return_sequences=True,input_shape=(10, 4)))
        model.add(LSTM(50,return_sequences=True,dropout=0.05,recurrent_dropout=0.05,input_shape=(100, 6)))
        model.add(LSTM(100,return_sequences=True,dropout=0.05,recurrent_dropout=0.05,input_shape=(100, 6)))
  #      model.add(LSTM(50,return_sequences=True,input_shape=(10, 4)))
        model.add(LSTM(50,dropout=0.05,recurrent_dropout=0.05))
        model.add(Dense(2))
        model.compile(loss='mean_absolute_error', optimizer='adam', metrics=['accuracy'])
        model.fit(sen, historym[101:size], epochs=10, batch_size=10)

    if btn_msg.rear_toggle:
        global sens
        global vel
        cmd = Twist()
        
        data = np.hstack((sens, vel))
        data = data.reshape(1,-1,6)
        predicted = model.predict(data)
        cmd.linear.x = predicted[0][0]
        cmd.angular.z = predicted[0][1]
        pub.publish(cmd)
        vel = np.vstack((vel, predicted))
        vel = vel[1:101, ]

if  __name__ == '__main__':
    rospy.init_node('replay')
    sens = [[0]*4]*100
    vel = [[0]*2]*100

    history = [0, 0, 0, 0, 0, 0]
    historym = [0, 0]
    
    sensor_values = LightSensorValues()
    episode = Event()
    on = ButtonValues()
    model = Sequential()    

    rospy.Subscriber('/event',Event,event_callback)
    rospy.Subscriber('/lightsensors',LightSensorValues,sensor_callback)
    rospy.Subscriber('/buttons',ButtonValues,button_callback,queue_size=1)
    pub = rospy.Publisher('/cmd_vel',Twist,queue_size=1)
    led_pub = rospy.Publisher('/leds',LedValues,queue_size=1)
    
    rospy.spin()


