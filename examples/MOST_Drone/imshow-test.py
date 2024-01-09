# Python program to explain cv2.imshow() method 

# importing cv2 
import cv2 
import time

# path 
path = r'D:\Drone_Project\Virtual_env\crazyflie-lib-python\examples\MOST_Drone\white_bg.png'

# Reading an image in default mode 
image = cv2.imread(path) 

# Window name in which image is displayed 
window_name = 'image'

# Using cv2.imshow() method 
# Displaying the image 
cv2.imshow(window_name, image) 

st = time.time()
# waits for user to press any key 
# (this is necessary to avoid Python kernel form crashing) 
cv2.waitKey(500) 

sst = time.time()
# time.sleep(2)

# closing all open windows 
cv2.destroyAllWindows() 

print("show time: ", sst-st)