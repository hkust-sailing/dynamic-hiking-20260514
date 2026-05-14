import numpy as np
from scipy.linalg import solve
from scipy.spatial.transform import Rotation as R
import matplotlib.pyplot as plt


def _wrap_angle_rad(a):
    return (a + np.pi) % (2*np.pi) - np.pi

class ControlAlgorithm:
    def __init__(self, M, D, K, dt=0.01):
        self.M = np.array(M, dtype=float)
        self.D = np.array(D, dtype=float)
        self.K = np.array(K, dtype=float)
        self.dt = dt
        self.reset()

    def reset(self, initial_x_d=None):
        # Internal convention: first 3 entries are angles in radians; last 3 are position.
        self.x_d = np.zeros(6, dtype=float)
        self.x_d_dot = np.zeros(6, dtype=float)
        self.x_d_ddot = np.zeros(6, dtype=float)

        self.x_e = np.zeros(6, dtype=float)        # error: [rot(rad); pos(m)]
        self.x_e_dot = np.zeros(6, dtype=float)    # rates: [rot_dot(rad/s); pos_dot(m/s)]
        self.x_e_ddot = np.zeros(6, dtype=float)

        self.R_e = np.eye(3)   # current deviation rotation matrix
        self.R_d = np.eye(3)   # desired rotation matrix

        if initial_x_d is not None:
            self.set_desired_trajectory(initial_x_d)

    def set_desired_trajectory(self, x_d, x_d_dot=None, x_d_ddot=None, deg_input=True):
        # x_d: [rx, ry, rz, x, y, z], with optional degree input for rotation.
        arr = np.array(x_d, dtype=float)
        if deg_input:
            arr[:3] = np.deg2rad(arr[:3])   # convert to radians for internal use
        self.x_d = arr
        self.R_d = R.from_euler('xyz', self.x_d[:3], degrees=False).as_matrix()
        if x_d_dot is not None:
            self.x_d_dot = np.array(x_d_dot, dtype=float)
        if x_d_ddot is not None:
            self.x_d_ddot = np.array(x_d_ddot, dtype=float)

    def _transform_force_to_world(self, F_sensor, current_pose):
        # unchanged from your code (ensure order matches x_e ordering: [torque, force])
        rot = R.from_euler('xyz', current_pose[:3], degrees=True).as_matrix()
        force_sensor = F_sensor[3:]
        torque_sensor = F_sensor[:3]
        force_world = rot @ force_sensor
        torque_world = rot @ torque_sensor
        return np.concatenate([torque_world, force_world])

    def update(self, F_sensor, current_pose=None):
        # 1) ensure self.x_e[:3] contains the current orientation error (rad) BEFORE computing accelerations
        cur_euler = R.from_matrix(self.R_e).as_euler('xyz', degrees=False)  # rad
        rot_err = cur_euler - self.x_d[:3]
        rot_err = _wrap_angle_rad(rot_err)
        self.x_e[:3] = rot_err  # now K @ x_e will include rotational stiffness (in radians)

        # 2) force transform and safety clipping (as you had)
        F_world = self._transform_force_to_world(F_sensor, current_pose)
        # ...clip F_world if needed...

        # 3) compute accelerations (use solve instead of inv)
        rhs = F_world - (self.D @ self.x_e_dot) - (self.K @ self.x_e)
        self.x_e_ddot = solve(self.M, rhs)

        # 4) integrate velocities
        self.x_e_dot += self.x_e_ddot * self.dt

        # 5) integrate position (translational part)
        self.x_e[3:] += self.x_e_dot[3:] * self.dt

        # 6) integrate rotation via small-angle Rodrigues using omega in rad/s
        omega = self.x_e_dot[:3]   # now already rad/s
        omega_skew = np.array([
            [0, -omega[2], omega[1]],
            [omega[2], 0, -omega[0]],
            [-omega[1], omega[0], 0]
        ])
        delta_R = np.eye(3) + omega_skew * self.dt + 0.5 * (omega_skew @ omega_skew) * (self.dt**2)
        self.R_e = delta_R @ self.R_e

        # 7) update orientation error after rotation integration (for next iteration)
        new_euler = R.from_matrix(self.R_e).as_euler('xyz', degrees=False)
        new_rot_err = _wrap_angle_rad(new_euler - self.x_d[:3])
        self.x_e[:3] = new_rot_err

        # 8) prepare target_pos to send out (we return angles in degrees if you need that)
        target_pos = np.zeros(6, dtype=float)
        target_pos[:3] = np.rad2deg(new_euler)   # degrees for external systems if they expect deg
        target_pos[3:] = self.x_d[3:] + self.x_e[3:]
        return target_pos
#test
# Example usage
M = np.diag([1,1,1,1,1,1])  # Example mass matrix
D = np.diag([20, 10, 10, 5, 5, 5])  # Example damping matrix
K = np.diag([100, 100, 100, 50, 50, 50])  # Example stiffness matrix

control = ControlAlgorithm(M, D, K)
control.set_desired_trajectory([0,0,0,0,0,0])
# Example force input
F_e = np.array([10, 50, 100, 10, 10, 10])
target_pos = [0,0,0,0,0,0]
Traj=[]
for i in range(400):
    target_pos = control.update(F_e, target_pos)
    # print("Target pose:", [f"{val:.6f}" for val in target_pos])
    Traj.append(target_pos.copy())

trajectory = np.array(Traj)

plt.figure(figsize=(7, 4))
time = np.arange(trajectory.shape[0])

for i in range(0,6):
    plt.plot(time, trajectory[:, i], label=f'Axis {i+1}')

plt.xlabel('Time step')
plt.ylabel('Position')
plt.title('Target position — all 6 axes')
plt.legend()
plt.tight_layout()
plt.show()