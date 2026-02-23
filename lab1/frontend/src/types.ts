export type Location = {
  lat: number;
  lon: number;
};

export type User = {
  id: string;
  fullName: string;
  email: string;
  age: number;
  drivingLicenseNumber: string;
  paymentToken: string;
  licenseValidUntil: string;
  location: Location;
  activeRentalVin?: string | null;
  clientId?: string;
};

export type Car = {
  vin: string;
  location: Location;
  status: string;
  rentedByUserId?: string | null;
  telematicsClientId?: string | null;
  distanceKm?: number;
};

export type Rental = {
  id: string;
  userId: string;
  vin: string;
  startedAt: string;
  endedAt?: string | null;
};
