//! Platform subsystem - query device information and firmware details

use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use pyo3_stub_gen_derive::*;
use std::sync::Arc;
use tokio::runtime::Runtime;
use tokio::sync::Mutex;
use futures::stream::Stream;
use futures::sink::Sink;
use std::pin::Pin;

use crate::error::to_pyerr;

/// Access to platform services
///
/// The platform CRTP port hosts a couple of utility services. This range from fetching the version of the firmware
/// and CRTP protocol, communication with apps using the App layer to setting the continuous wave radio mode for
/// radio testing.
#[gen_stub_pyclass]
#[pyclass]
pub struct Platform {
    pub(crate) cf: Arc<crazyflie_lib::Crazyflie>,
    pub(crate) runtime: Arc<Runtime>,
}

#[gen_stub_pymethods]
#[pymethods]
impl Platform {
    /// Fetch the protocol version from the Crazyflie
    ///
    /// The protocol version is updated when new message or breaking change are
    /// implemented in the protocol.
    /// Compatibility is checked at connection time.
    fn get_protocol_version(&self) -> PyResult<u8> {
        self.runtime.block_on(async {
            self.cf.platform.protocol_version().await
        }).map_err(to_pyerr)
    }

    /// Fetch the firmware version
    ///
    /// If this firmware is a stable release, the release name will be returned for example ```2021.06```.
    /// If this firmware is a git build, between releases, the number of commit since the last release will be added
    /// for example ```2021.06 +128```.
    fn get_firmware_version(&self) -> PyResult<String> {
        self.runtime.block_on(async {
            self.cf.platform.firmware_version().await
        }).map_err(to_pyerr)
    }

    /// Fetch the device type.
    ///
    /// The Crazyflie firmware can run on multiple device. This function returns the name of the device. For example
    /// ```Crazyflie 2.1``` is returned in the case of a Crazyflie 2.1.
    fn get_device_type_name(&self) -> PyResult<String> {
        self.runtime.block_on(async {
            self.cf.platform.device_type_name().await
        }).map_err(to_pyerr)
    }

    /// Set radio in continuous wave mode
    ///
    /// If activate is set to true, the Crazyflie's radio will transmit a continuous wave at the current channel
    /// frequency. This will be active until the Crazyflie is reset or this function is called with activate to false.
    ///
    /// Setting continuous wave will:
    ///  - Disconnect the radio link. So this function should practically only be used when connected over USB
    ///  - Jam any radio running on the same frequency, this includes Wifi and Bluetooth
    ///
    /// As such, this shall only be used for test purpose in a controlled environment.
    fn set_continuous_wave(&self, activate: bool) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.platform.set_cont_wave(activate).await
        }).map_err(to_pyerr)
    }

    /// Send system arm/disarm request
    ///
    /// Arms or disarms the Crazyflie's safety systems. When disarmed, the motors
    /// will not spin even if thrust commands are sent.
    ///
    /// # Arguments
    /// * `do_arm` - true to arm, false to disarm
    fn send_arming_request(&self, do_arm: bool) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.platform.send_arming_request(do_arm).await
        }).map_err(to_pyerr)
    }

    /// Send crash recovery request
    ///
    /// Requests recovery from a crash state detected by the Crazyflie.
    fn send_crash_recovery_request(&self) -> PyResult<()> {
        self.runtime.block_on(async {
            self.cf.platform.send_crash_recovery_request().await
        }).map_err(to_pyerr)
    }

    /// Get the bidirectional app channel for custom communication
    ///
    /// The app channel allows bidirectional communication between ground software
    /// and custom apps running on the Crazyflie. This is useful for implementing
    /// custom protocols without defining new CRTP packets.
    ///
    /// Note: This channel can only be acquired once per connection. Subsequent
    /// calls will return None.
    ///
    /// # Returns
    /// * Optional AppChannel object, or None if already acquired
    fn get_app_channel(&self) -> PyResult<Option<AppChannel>> {
        self.runtime.block_on(async {
            if let Some((tx, rx)) = self.cf.platform.get_app_channel().await {
                Ok(Some(AppChannel::new(tx, rx, self.runtime.clone())))
            } else {
                Ok(None)
            }
        })
    }
}

use tokio::sync::mpsc;

/// Bidirectional communication channel with Crazyflie apps
///
/// The app channel provides both send and receive capabilities for custom
/// communication with apps running on the Crazyflie firmware. Packets are
/// limited to 31 bytes (APPCHANNEL_MTU).
#[gen_stub_pyclass]
#[pyclass]
pub struct AppChannel {
    runtime: Arc<Runtime>,
    send_tx: mpsc::UnboundedSender<Vec<u8>>,
    recv_rx: Arc<Mutex<mpsc::UnboundedReceiver<Vec<u8>>>>,
}

impl AppChannel {
    /// Create a new AppChannel instance
    fn new(
        mut tx: impl Sink<crazyflie_lib::subsystems::platform::AppChannelPacket> + Send + Unpin + 'static,
        mut rx: impl Stream<Item = crazyflie_lib::subsystems::platform::AppChannelPacket> + Send + Unpin + 'static,
        runtime: Arc<Runtime>
    ) -> Self {
        use futures::sink::SinkExt;
        use futures::stream::StreamExt;

        // Create channels for bridging
        let (send_tx, mut send_rx) = mpsc::unbounded_channel::<Vec<u8>>();
        let (recv_tx, recv_rx) = mpsc::unbounded_channel::<Vec<u8>>();

        // Spawn task to handle sending
        runtime.spawn(async move {
            while let Some(data) = send_rx.recv().await {
                if let Ok(packet) = crazyflie_lib::subsystems::platform::AppChannelPacket::try_from(data) {
                    let _ = tx.send(packet).await;
                }
            }
        });

        // Spawn task to handle receiving
        runtime.spawn(async move {
            while let Some(packet) = rx.next().await {
                let data: Vec<u8> = packet.into();
                let _ = recv_tx.send(data);
            }
        });

        AppChannel {
            runtime,
            send_tx,
            recv_rx: Arc::new(Mutex::new(recv_rx)),
        }
    }
}

#[gen_stub_pymethods]
#[pymethods]
impl AppChannel {
    /// Send a data packet to the Crazyflie app
    ///
    /// Sends raw bytes to a custom app running on the Crazyflie. The packet
    /// must not exceed 31 bytes (APPCHANNEL_MTU).
    ///
    /// # Arguments
    /// * `data` - Bytes to send (maximum 31 bytes)
    ///
    /// # Raises
    /// * ValueError - If data exceeds 31 bytes
    fn send(&self, data: Vec<u8>) -> PyResult<()> {
        // Validate packet size
        if data.len() > 31 {
            return Err(PyValueError::new_err(
                format!("App channel packet too large: {} bytes (max 31)", data.len())
            ));
        }

        self.send_tx.send(data)
            .map_err(|_| PyValueError::new_err("AppChannel send has been closed"))?;
        Ok(())
    }

    /// Receive buffered data packets from the Crazyflie app
    ///
    /// Returns all buffered packets received from the Crazyflie app. This
    /// function will return up to 100 packets with a 10ms timeout per packet.
    ///
    /// The library keeps track of all packets received since the channel was
    /// acquired, so the first call may return multiple buffered packets.
    ///
    /// # Returns
    /// * List of received data packets (each up to 31 bytes)
    fn receive(&self) -> PyResult<Vec<Vec<u8>>> {
        self.runtime.block_on(async {
            let mut rx_guard = self.recv_rx.lock().await;
            let mut packets = Vec::new();

            // Get up to 100 packets or timeout
            for _ in 0..100 {
                if let Ok(Some(packet)) = tokio::time::timeout(
                    std::time::Duration::from_millis(10),
                    rx_guard.recv()
                ).await {
                    packets.push(packet);
                } else {
                    break;
                }
            }

            Ok(packets)
        })
    }
}
