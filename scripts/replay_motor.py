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


class Replay():
    def __init__(self):
        self.len_sequence = 100
        self.sensor = [[0]*4] * self.len_sequence
        self.vel = [[0]*2] * self.len_sequence

        self.history = [0, 0, 0, 0, 0, 0]
        self.history_motor = [0, 0]

        self.sensor_values = LightSensorValues()
        self.episode = Event()
        self.on = ButtonValues()

        rospy.Subscriber('/event',Event,self.event_callback)
        rospy.Subscriber('/lightsensors',LightSensorValues,self.sensor_callback)
        rospy.Subscriber('/buttons',ButtonValues,self.button_callback,queue_size=1)
        self.pub = rospy.Publisher('/cmd_vel',Twist,queue_size=1)
        self.led_pub = rospy.Publisher('/leds',LedValues,queue_size=1)


    def event_callback(self,eve):
        e = eve
        episode = [e.right_forward, e.right_side, e.left_side, e.left_forward,e.linear_x, e.angular_z]
   	episode_motor = [e.linear_x, e.angular_z]

        self.history = np.vstack((self.history, episode))  
        self.history_motor = np.vstack((self.history_motor, episode_motor)) 


    def sensor_callback(self,messages):
        s = messages
        sensor_new = [s.right_forward, s.right_side, s.left_side, s.left_forward]
        self.sensor = np.vstack((self.sensor, sensor_new))
        self.sensor = self.sensor[1: self.len_sequence + 1,]

    def button_callback(self,btn_msg):
        leds = LedValues()
        leds.left_side = btn_msg.front_toggle
        leds.left_forward = btn_msg.mid_toggle
        leds.right_forward = btn_msg.rear_toggle
        self.led_pub.publish(leds)
        self.on = btn_msg
        if btn_msg.mid:
            step = 1
            self.size = len (self.history)
               
            self.history = self.history.reshape(1,-1,6)
            history_train = self.history[ : , step : step + self.len_sequence, ]
            step += 1

            for i in range(self.size - self.len_sequence - 2):
                temp = self.history[ : , step : step + self.len_sequence, ]
                history_train = np.vstack((history_train, temp))
                step += 1
            
            self.model = Sequential() 
#            self.model.add(LSTM(50,return_sequences=True,dropout=0.05,recurrent_dropout=0.05,input_shape=(self.len_sequence, 6)))
#            self.model.add(LSTM(50,return_sequences=True,dropout=0.05,recurrent_dropout=0.05,input_shape=(self.len_sequence, 6)))
            self.model.add(LSTM(50,dropout=0.05,recurrent_dropout=0.05))
            self.model.add(Dense(2))
            self.model.compile(loss='mean_absolute_error', optimizer='adam', metrics=['accuracy'])
            self.model.fit(history_train, self.history_motor[self.len_sequence+1:self.size], epochs=30, batch_size=32)
            self.a = 0

        if btn_msg.rear_toggle:
            if self.a == 0:

                self.a = 1
                self.vel =  self.history_motor[self.size - self.len_sequence :self.size]
            else:
                cmd = Twist()
        
                data = np.hstack((self.sensor, self.vel))
                data = data.reshape(1,-1,6)
                predicted = self.model.predict(data)
                cmd.linear.x = predicted[0][0]
                cmd.angular.z = predicted[0][1]
                self.pub.publish(cmd)
                self.vel = np.vstack((self.vel, predicted))
                self.vel = self.vel[1:self.len_sequence + 1, ]

if  __name__ == '__main__':
    rospy.init_node('replay')
    Replay()
    rospy.spin()
