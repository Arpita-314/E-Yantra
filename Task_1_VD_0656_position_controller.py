#!/usr/bin/env python

from vitarana_drone.msg import *
from pid_tune.msg import PidTune
from sensor_msgs.msg import NavSatFix
from std_msgs.msg import Float32
import rospy
import time
import tf

class Edrone():
	def __init__(self):
		rospy.init_node("position_controller")

		self.set_loc = [19.0007046575,71.9998955286,22.1599967919] # to ser the goal location from 0.31 altitude to 3m and than displacement in latitude     
		self.current_loc=[0.0,0.0,0.0] # to store the current location of drone

		self.error = [0,0,0] # to store the eroor in latitude,longitude,altitude
		self.out_throttle=0.0 # to store the required throttle speed
		self.out_pitch=0.0 # to store the required pitch speed
		self.out_roll = 0.0
		self.prev_error=[0.0,0.0,0.0] # to store previous error used in derivative pid error
		
		#to initialise the prop speed
		self.rypt_cmd = edrone_cmd() 
		self.rypt_cmd.rcRoll = 0.0
		self.rypt_cmd.rcPitch = 0.0
		self.rypt_cmd.rcYaw = 0.0
		self.rypt_cmd.rcThrottle = 0.0

		#to store the value to be published of altitude and latitude error
		self.altitude_error = Float32()
		self.latitude_error = Float32()
		self.longitude_error = Float32()
		self.altitude_error.data = 0
		self.latitude_error.data = 0
		self.longitude_error.data = 0

		# acts as reference line 
		self.zero =Float32()
		self.zero.data=0.0
		
		#storing the tuned value of latititude,longitude and altitude respectively
		self.kp = [32000,19800,110]
		self.ki = [0,0,0]
		self.kd = [9500000,5864000,3930]

		self.Iterm=[0.0,0.0,0.0]
		self.out_lat=0.0
		self.out_long=0.0
		self.out_alt=0.0

		self.sample_time = 40

		self.attitude_input_pub = rospy.Publisher('/drone_command', edrone_cmd,queue_size=1) 
		self.altitude_out_pub = rospy.Publisher('/altitude_error', Float32,queue_size=1)
		self.zero_error_pub = rospy.Publisher('/zero_error',Float32,queue_size=1)
		self.latitude_error_pub = rospy.Publisher('/latitude_error',Float32,queue_size=1) 
		self.longitude_error_pub = rospy.Publisher('/longitude_error',Float32,queue_size=1) 
		
		rospy.Subscriber('/edrone/gps', NavSatFix, self.loc_callback)
		#rospy.Subscriber('/pid_tuning_altitude',PidTune, self.altitude_set_pid)
		#rospy.Subscriber('/pid_tuning_pitch', PidTune, self.latitude_set_pid)
		#rospy.Subscriber('/pid_tuning_roll', PidTune, self.longitude_set_pid)
        	

	def loc_callback(self,msg):
		self.current_loc[0] = msg.latitude
		self.current_loc[1] = msg.longitude
		self.current_loc[2] = msg.altitude
	   
	def altitude_set_pid(self, altitude):

		self.kp[2] = altitude.Kp *1
		self.ki[2] = altitude.Ki *0.08
		self.kd[2] = altitude.Kd *5

	def latitude_set_pid(self, pitch):
		self.kp[0] = pitch.Kp *100
		self.ki[0] = pitch.Ki *1
		self.kd[0] = pitch.Kd *5000

	def longitude_set_pid(self, roll):
		self.kp[1] = roll.Kp *100
		self.ki[1] = roll.Ki *1
		self.kd[1] = roll.Kd *5000	

	def error_calc(self,target,current):
		error = target - current
		return error

	def pid_error(self,i):
		self.Iterm[i]=(self.Iterm[i]+self.error[i])*self.ki[i]
		pid_error= self.kp[i]*self.error[i] + self.Iterm[i] + (self.error[i] - self.prev_error[i])*self.kd[i]
		return pid_error
	def pid_p(self):


		#altitude 
		if(self.current_loc[1]>=(self.set_loc[1]-0.000001)): 
			adjusted_alt = self.set_loc[2]
		else:
			adjusted_alt = self.set_loc[2]+5
		self.error[2]= self.error_calc(adjusted_alt,self.current_loc[2])
		self.out_alt = self.pid_error(2)
		self.altitude_error.data = self.error[2]
		self.prev_error[2]=self.error[2]
		
		if(self.current_loc[2]==(self.set_loc[2])):
			time.sleep(1)

		#latitude	
		if(self.current_loc[2]<(adjusted_alt+0.2) and self.current_loc[2]>=(adjusted_alt)): 
			self.error[0]= self.error_calc(self.set_loc[0],self.current_loc[0])
			self.out_lat = self.pid_error(0)
			self.latitude_error.data = self.error[0]
			self.prev_error[0]=self.error[0]
			#longitude
			if(self.current_loc[0]>=(self.set_loc[0]-0.000001)):
				self.error[1]= self.error_calc(self.set_loc[1],self.current_loc[1])
				self.out_long = self.pid_error(1)
				self.longitude_error.data = self.error[1]
				self.prev_error[1]=self.error[1]
			
		# to change set point once required altitude and latitude is reached to land the drone on required location


		self.out_throttle= 1500 + self.out_alt
		self.out_pitch=1500 + self.out_lat
		self.out_roll = 1500 + self.out_long


		self.rypt_cmd.rcRoll= self.out_roll
		self.rypt_cmd.rcYaw = 1500.0
		self.rypt_cmd.rcPitch = self.out_pitch
		self.rypt_cmd.rcThrottle = self.out_throttle

		self.zero.data = 0

		self.zero_error_pub.publish(self.zero)
		self.altitude_out_pub.publish(self.altitude_error)
		self.latitude_error_pub.publish(self.latitude_error)
		self.longitude_error_pub.publish(self.longitude_error)
		self.attitude_input_pub.publish(self.rypt_cmd)


if __name__ == '__main__':

	e_drone = Edrone()
	r = rospy.Rate(e_drone.sample_time)  # specify rate in Hz based upon your desired PID sampling time, i.e. if desired sample time is 33ms specify rate as 30Hz
	while not rospy.is_shutdown():
		e_drone.pid_p()
		r.sleep()
