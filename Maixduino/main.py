import machine, utime, time, network, image, lcd
from machine import I2C
import BlynkLib
from BlynkTimer import BlynkTimer
import KPU as kpu

SSID = "ARRIS-A1A2"
PASW = "543609298A95A4A2"

BLYNK_AUTH = 'BBLPlaYju01FNB9QRuppPZ8ZzQ2WdqR6'
#BLYNK_AUTH = 'HVdPy1XCkVSzFegwKSTvPGbRbU5v_SPl'

#--------------------------WIFI--------------------------#

def enable_esp32():
    from network_esp32 import wifi
    if wifi.isconnected() == False:
        for i in range(5):
            try:
                wifi.reset(is_hard=True)
                print('try AT connect wifi...')
                wifi.connect(SSID, PASW)
                if wifi.isconnected():
                    break
            except Exception as e:
                print(e)
    print('network state:', wifi.isconnected(), wifi.ifconfig())

enable_esp32()

#--------------------------ACELEROMETRO--------------------------#

i2c = I2C (I2C.I2C0, freq = 400000, scl = 30, sda = 31)

#Direccion MPU6050
MPU6050_ADDR = 0x68

#Registros acelerometro
MPU6050_ACCEL_XOUT_H = 0x3B
MPU6050_ACCEL_XOUT_L = 0x3C
MPU6050_ACCEL_YOUT_H = 0x3D
MPU6050_ACCEL_YOUT_L = 0x3E
MPU6050_ACCEL_ZOUT_H = 0x3F
MPU6050_ACCEL_ZOUT_L = 0x40

#Enable
MPU6050_PWR_MGMT_1 = 0x6B

#Escala acelerometro = 16g
MPU6050_LSBG = (9.81 / 16384.0)

#SMPLRT_DIV
i2c.writeto_mem(MPU6050_ADDR, 0x19, 0b00000000)

#DLPF_FILTER 44Hz
i2c.writeto_mem(MPU6050_ADDR, 0x1A, 0b00000011)

#GYRO 2000
i2c.writeto_mem(MPU6050_ADDR, 0x1B, 0b00011000)

#ACEL 16g
i2c.writeto_mem(MPU6050_ADDR, 0x1C, 0b00000000)

#FIFO DISABLED
i2c.writeto_mem(MPU6050_ADDR, 0x23, 0b00000000)

def mpu6050_init(i2c):
    i2c.writeto_mem(MPU6050_ADDR, MPU6050_PWR_MGMT_1, 0b00001000)

def combine_register_values(h, l):
    if not h[0] & 0x80:
        return h[0] << 8 | l[0]
    return -(((h[0] ^ 255) << 8) |  (l[0] ^ 255) + 1)

def mpu6050_get_accel(i2c):
    accel_x_h = i2c.readfrom_mem(MPU6050_ADDR, MPU6050_ACCEL_XOUT_H, 1)
    accel_x_l = i2c.readfrom_mem(MPU6050_ADDR, MPU6050_ACCEL_XOUT_L, 1)
    accel_y_h = i2c.readfrom_mem(MPU6050_ADDR, MPU6050_ACCEL_YOUT_H, 1)
    accel_y_l = i2c.readfrom_mem(MPU6050_ADDR, MPU6050_ACCEL_YOUT_L, 1)
    accel_z_h = i2c.readfrom_mem(MPU6050_ADDR, MPU6050_ACCEL_ZOUT_H, 1)
    accel_z_l = i2c.readfrom_mem(MPU6050_ADDR, MPU6050_ACCEL_ZOUT_L, 1)

    return [combine_register_values(accel_x_h, accel_x_l) * MPU6050_LSBG,
            combine_register_values(accel_y_h, accel_y_l) * MPU6050_LSBG,
            combine_register_values(accel_z_h, accel_z_l) * MPU6050_LSBG]

mpu6050_init(i2c)

blynk = BlynkLib.Blynk(BLYNK_AUTH)
timer = BlynkTimer()

#task = kpu.load('/sd/last.kmodel')
task = kpu.load(0x300000)

dummyImage = image.Image()
dummyImage = dummyImage.resize(20, 10)
image_data_array = []
counter = 0
notify = 0

##############
#last_bk
#LABELS = ['Walking', 'Jumping', 'Fall', 'Standing']
##############

LABELS = ['Walking', 'Jumping', 'Fall', 'Standing']

while True:

    blynk.run()
    timer.run()

    counter = counter + 1
    data = mpu6050_get_accel(i2c)
    accel_x = int((data[0] + 20 ) * 6)
    accel_y = int((data[1] + 20 ) * 6)
    accel_z = int((data[2] + 20 ) * 6)
    image_data_array.append([accel_x, accel_y, accel_z])

    if counter >= 200:
        #image_data_array.pop(0)
        for h in range(0, 10):
            for w in range(0, 20):
                dummyImage.set_pixel(w, h,
                (image_data_array[h * 20 + w][0], image_data_array[h * 20 + w][1], image_data_array[h * 20 + w][2]))
        image_data_array.clear()
        #dummyImage.save('sd//images/' + str(time.time()) + '.jpg')
        #dummyImage.save(str(time.time()) + '.jpg')
        dummyImage.pix_to_ai()
        fmap = kpu.forward(task, dummyImage)
        plist = fmap[:]
        pmax = max(plist)
        max_index = plist.index(pmax)

        def ResetNotification():
            global notify
            notify = 0

        def Notification():
            global notify
            if notify == 0:
                blynk.set_property(2, 'color', '#FF0000')
                blynk.notify('Se ha producido una emergencia')
                #blynk.email("pruebascarlos78@gmail.com", 'Detección emergencia', 'El dispositivo ha detectado una posible emergencia')
                timer.set_timeout(30, ResetNotification)
                notify = 1

        @blynk.VIRTUAL_READ(2)
        def my_read_handler():
            blynk.set_property(2, 'color', '#FFFFFF')
            blynk.virtual_write(2, LABELS[max_index])
            if LABELS[max_index] == 'Fall':
                Notification()
            if LABELS[max_index] != 'Fall':
                ResetNotification()

        print (LABELS[max_index])
        counter = 0

    utime.sleep_ms(10)

