const Booking = require("../models/Booking");
const Service = require("../models/Service");
const User = require("../models/User");

// Create a new booking
exports.createBooking = async (req, res) => {
  try {
    const { serviceId, date, time, amount, paymentId } = req.body;
    if (!serviceId || !date || !time || !amount) {
      return res.status(400).json({ message: "Missing required fields." });
    }
    const service = await Service.findById(serviceId).populate("provider");
    if (!service) return res.status(404).json({ message: "Service not found." });
    // Find the slot
    const slotIdx = service.availability.findIndex(slot => {
      return (
        new Date(slot.date).toISOString() === new Date(date).toISOString() &&
        slot.time === time
      );
    });
    if (slotIdx === -1) {
      return res.status(400).json({ message: "Selected slot is not available." });
    }
    const slot = service.availability[slotIdx];
    if (slot.registeredCount >= slot.maxCapacity) {
      return res.status(400).json({ message: "This slot is fully booked." });
    }
    // Increment registeredCount
    service.availability[slotIdx].registeredCount += 1;
    await service.save();
    const booking = new Booking({
      user: req.user.id,
      provider: service.provider._id,
      service: serviceId,
      date,
      time,
      amount,
      paymentStatus: paymentId ? "paid" : "pending",
      paymentId: paymentId || undefined
    });
    await booking.save();
    res.json(booking);
  } catch (err) {
    res.status(500).json({ message: err.message || "Failed to create booking." });
  }
};

// List bookings for current user
exports.myBookings = async (req, res) => {
  try {
    const bookings = await Booking.find({ user: req.user.id })
      .populate("service provider user");
    res.json(bookings);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
};

// List bookings for provider (with user and slot info)
exports.providerBookings = async (req, res) => {
  try {
    const bookings = await Booking.find({ provider: req.user.id })
      .populate("user", "name email profilePic")
      .populate("service", "name availability");
    res.json(bookings);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
};

// Provider confirms or rejects a booking
exports.confirmBooking = async (req, res) => {
  try {
    const { bookingId, status } = req.body;
    if (!['confirmed', 'rejected'].includes(status)) {
      return res.status(400).json({ message: 'Invalid status' });
    }
    const booking = await Booking.findById(bookingId);
    if (!booking) return res.status(404).json({ message: 'Booking not found.' });
    // Only provider can confirm/reject
    if (booking.provider.toString() !== req.user.id) {
      return res.status(403).json({ message: 'Not authorized' });
    }
    booking.status = status;
    await booking.save();
    res.json(booking);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
};

// Update payment status
exports.updatePaymentStatus = async (req, res) => {
  try {
    const { bookingId, status, paymentId } = req.body;
    const booking = await Booking.findById(bookingId);
    if (!booking) return res.status(404).json({ message: "Booking not found." });
    booking.paymentStatus = status;
    if (paymentId) booking.paymentId = paymentId;
    await booking.save();
    res.json(booking);
  } catch (err) {
    res.status(500).json({ message: err.message });
  }
};
