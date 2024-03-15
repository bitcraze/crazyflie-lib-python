# Python program to explain cv2.imshow() method 

# importing cv2 
import cv2 
import time

# # path 
# path = r'D:\Drone_Project\Virtual_env\crazyflie-lib-python\examples\MOST_Drone\white_bg.png'

# # Reading an image in default mode 
# image = cv2.imread(path) 

# # Window name in which image is displayed 
# window_name = 'image'

# # Using cv2.imshow() method 
# # Displaying the image 
# cv2.imshow(window_name, image) 

# st = time.time()
# # waits for user to press any key 
# # (this is necessary to avoid Python kernel form crashing) 
# cv2.waitKey(5000) 

# sst = time.time()
# # time.sleep(2)

# # closing all open windows 
# cv2.destroyAllWindows() 

# print("show time: ", sst-st)



## for showing image
# paths
path_rest = r'D:\Drone_Project\Virtual_env\crazyflie-lib-python\examples\MOST_Drone\bg_rest.png'
path_task = r'D:\Drone_Project\Virtual_env\crazyflie-lib-python\examples\MOST_Drone\bg_task.png'
  
# Reading an image in default mode 
image_r = cv2.imread(path_rest) 
image_t = cv2.imread(path_task)
  
# Window name in which image is displayed 
window_name = 'image'

# Displaying the image for 4 seconds
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN,
                          cv2.WINDOW_FULLSCREEN)
cv2.imshow(window_name, image_r) 
sr = time.time()
cv2.waitKey(4000)
ssr = time.time()
# cv2.destroyAllWindows()

# Displaying the image for 4 seconds
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN,
                          cv2.WINDOW_FULLSCREEN)
cv2.imshow(window_name, image_t)
st = time.time()
cv2.waitKey(1000)
sst = time.time()
cv2.destroyAllWindows()

print("show time rest: ", ssr-sr)

print("show time task: ", sst-st)


t = time.time()
time.sleep(5)
tt = time.time()
print("show time: ", tt-t)
