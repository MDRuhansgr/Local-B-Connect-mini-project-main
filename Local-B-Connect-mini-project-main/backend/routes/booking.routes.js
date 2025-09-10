const express = require("express");
const router = express.Router();
const bookingController = require("../controllers/booking.controller");
const auth = require("../middleware/auth");

// Create booking
router.post("/create", auth, bookingController.createBooking);
// User's bookings
router.get("/my", auth, bookingController.myBookings);
// Provider's bookings
router.get("/provider", auth, bookingController.providerBookings);
// Update payment status
router.post("/update-payment", auth, bookingController.updatePaymentStatus);
// Provider confirms/rejects booking
router.post("/confirm", auth, bookingController.confirmBooking);

module.exports = router;
