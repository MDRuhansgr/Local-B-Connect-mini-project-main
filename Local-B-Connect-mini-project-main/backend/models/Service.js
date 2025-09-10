const mongoose = require("mongoose");

const reviewSchema = new mongoose.Schema({
  user: { type: mongoose.Schema.Types.ObjectId, ref: "User" },
  comment: String,
  rating: { type: Number, min: 1, max: 5 }
});

const serviceSchema = new mongoose.Schema({
  provider: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true },
  name: { type: String, required: true },
  type: String,
  subtype: String,
  location: String,
  city: String,
  state: String,
  address: String,
  price: { type: Number },
  description: String,
  photos: [String],
  availability: [
    {
      date: { type: Date, required: true },
      time: { type: String, required: true },
      maxCapacity: { type: Number, required: true },
      registeredCount: { type: Number, default: 0 }
    }
  ],
  reviews: [reviewSchema],
  rating: { type: Number, default: 0 }
}, { timestamps: true });

module.exports = mongoose.model("Service", serviceSchema);
