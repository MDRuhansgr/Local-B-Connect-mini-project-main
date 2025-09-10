const Service = require("../models/Service");

const path = require("path");

// Helper to parse and sanitize availability input
function parseAvailability(avail) {
  if (!avail) return [];
  let arr = avail;
  if (typeof avail === 'string') {
    try {
      arr = JSON.parse(avail);
    } catch {
      return [];
    }
  }
  if (!Array.isArray(arr)) return [];
  return arr.map(slot => ({
    ...slot,
    maxCapacity: parseInt(slot.maxCapacity) || 1,
    registeredCount: parseInt(slot.registeredCount) || 0
  }));
}

exports.addService = async (req, res) => {
  try {
    // Support both JSON and multipart/form-data
    let photos = [];
    if (req.files && req.files.length) {
      photos = req.files.map(f => f.filename);
    } else if (req.body.photos) {
      if (Array.isArray(req.body.photos)) {
        photos = req.body.photos;
      } else if (typeof req.body.photos === 'string') {
        photos = [req.body.photos];
      }
    }

    // Map frontend fields to backend schema
    // Always ensure photos is an array of strings (filenames)
    let photosArr = photos;
    if (!photosArr.length && req.body.photos) {
      if (Array.isArray(req.body.photos)) {
        photosArr = req.body.photos.map(p => typeof p === 'object' && p.name ? p.name : p);
      } else if (typeof req.body.photos === 'string') {
        photosArr = [req.body.photos];
      }
    }
    const serviceData = {
      provider: req.user.id,
      name: req.body.name,
      type: req.body.category || req.body.type,
      description: req.body.description,
      price: req.body.price,
      availability: parseAvailability(req.body.availability),
      photos: photosArr,
      location: [req.body.city, req.body.state, req.body.address].filter(Boolean).join(", "),
      city: req.body.city,
      state: req.body.state,
      address: req.body.address,
    };

    // Validate required fields
    if (!serviceData.name || !serviceData.type || !serviceData.price) {
      return res.status(400).json({ message: "Missing required fields (name, category/type, or price)." });
    }
    const newService = new Service(serviceData);
    const saved = await newService.save();
    res.json(saved);
  } catch (err) {
    res.status(500).json({ message: err.message || "Failed to save service." });
  }
};

exports.updateService = async (req, res) => {
  try {
    let photos = [];
    if (req.files && req.files.length) {
      photos = req.files.map(f => f.filename);
    } else if (req.body.photos) {
      if (Array.isArray(req.body.photos)) {
        photos = req.body.photos;
      } else if (typeof req.body.photos === 'string') {
        photos = [req.body.photos];
      }
    }
    // Always ensure photos is an array of strings (filenames)
    let photosArr = photos;
    if (!photosArr.length && req.body.photos) {
      if (Array.isArray(req.body.photos)) {
        photosArr = req.body.photos.map(p => typeof p === 'object' && p.name ? p.name : p);
      } else if (typeof req.body.photos === 'string') {
        photosArr = [req.body.photos];
      }
    }
    const updateData = {
      availability: parseAvailability(req.body.availability),
      name: req.body.name,
      type: req.body.category || req.body.type,
      description: req.body.description,
      price: req.body.price,
      location: [req.body.city, req.body.state, req.body.address].filter(Boolean).join(", "),
      city: req.body.city,
      state: req.body.state,
      address: req.body.address,
      photos: photosArr
    };
    if (!updateData.name || !updateData.type || !updateData.price) {
      return res.status(400).json({ message: "Missing required fields (name, category/type, or price)." });
    }
    const updated = await Service.findByIdAndUpdate(req.params.id, updateData, { new: true });
    res.json(updated);
  } catch (err) {
    res.status(500).json({ message: err.message || "Failed to update service." });
  }
};

exports.deleteService = async (req, res) => {
  await Service.findByIdAndDelete(req.params.id);
  res.json({ message: "Service deleted" });
};

exports.verifyService = async (req, res) => {
  try {
    const { serviceId } = req.body;
    const service = await Service.findOne({ _id: serviceId, provider: req.user.id });
    if (!service) return res.status(404).json({ message: 'Service not found or not owned by you.' });
    service.verified = true;
    await service.save();
    res.json(service);
  } catch (err) {
    res.status(500).json({ message: err.message || 'Failed to verify service.' });
  }
};

exports.myServices = async (req, res) => {
  const services = await Service.find({ provider: req.user.id });
  res.json(services);
};

exports.getAllServices = async (req, res) => {
  const { location, type } = req.query;
  const filter = {};
  if (location) filter.location = location;
  if (type) filter.type = type;
  const services = await Service.find(filter).populate("provider", "name");
  res.json(services);
};

exports.addReview = async (req, res) => {
  const { comment, rating } = req.body;
  const service = await Service.findById(req.params.id);
  if (!service) return res.status(404).json({ message: "Service not found" });

  service.reviews.push({ user: req.user.id, comment, rating });

  // update average rating
  const avg = service.reviews.reduce((acc, r) => acc + r.rating, 0) / service.reviews.length;
  service.rating = avg.toFixed(1);

  await service.save();
  res.json({ message: "Review added" });
};

exports.getServiceDetails = async (req, res) => {
  const service = await Service.findById(req.params.id).populate("reviews.user", "name");
  if (!service) return res.status(404).json({ message: "Service not found" });
  res.json(service);
};
