import SwiftUI

struct PreviewJobView: View {
    @Bindable var viewModel: PostJobViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var success = false
    @State private var showPriceConfirmation = false
    private var payableText: String {
        guard let amount = viewModel.pricingQuote?.final_service_charge else { return "Quote unavailable" }
        return amount.formatted(.currency(code: "INR"))
    }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                HStack { Text(viewModel.category.rawValue).font(.system(size: 20, weight: .bold)); Spacer(); if viewModel.category.isDelivery { StatusBadge(text: "Delivery Job") } }
                Label(viewModel.location, systemImage: "mappin.and.ellipse").font(.system(size: 14)).foregroundStyle(.gray)
                if viewModel.isScheduled {
                    Text("Pre-Booking: \(viewModel.scheduledStartTime.formatted(date: .abbreviated, time: .omitted)) at \(viewModel.selectedTime):00").font(.system(size: 13))
                    Text("Worker requests will be sent four hours before this time.").font(.system(size: 12)).foregroundStyle(.secondary)
                } else { Text("Instant booking • worker requests sent immediately").font(.system(size: 13)) }
                if viewModel.category.isDelivery {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("📦 Pickup: \(viewModel.pickupLocation)")
                        Text("📍 Drop: \(viewModel.dropLocation)")
                    }.font(.system(size: 13, weight: .bold)).padding(12).background(Color.errnoBackground, in: RoundedRectangle(cornerRadius: 10))
                }
                WorkerLocationMapView(locationName: viewModel.category.isDelivery ? viewModel.pickupLocation : viewModel.location,
                                      distanceText: viewModel.location, isDarkTheme: false,
                                      latitude: viewModel.latitude, longitude: viewModel.longitude)
                Text(verbatim: viewModel.description).font(.system(size: 14, weight: .regular, design: .default)).foregroundColor(Color.errnoTextSecondary)
                Text("Fixed Time Options & Pay Structure").font(.system(size: 15, weight: .bold))
                HStack { Text("\(Int(viewModel.estimatedDurationHours)) hour duration"); Spacer(); Text(payableText).bold() }.font(.system(size: 14))
                quoteBreakdown
                Button(viewModel.isLoadingQuote ? "Refreshing quote…" : "Refresh price quote") { Task { await viewModel.refreshPricingQuote() } }
                    .disabled(viewModel.isLoadingQuote)
                if let error = viewModel.errorMessage { Text(error).foregroundStyle(Color.errnoError) }
            }.marketplaceCard(padding: 20).padding(20).frame(maxWidth: 800).frame(maxWidth: .infinity)
        }.marketplacePage().navigationTitle("Preview Job").navigationBarTitleDisplayMode(.inline)
            .toolbar(.visible, for: .navigationBar)
            .navigationBarBackButtonHidden(viewModel.isSubmitting || success)
            .safeAreaInset(edge: .bottom) {
                HStack(spacing: 12) {
                    PrimaryButton(title: "Edit", style: .secondary, isDisabled: viewModel.isSubmitting) { dismiss() }
                    PrimaryButton(title: viewModel.pricingQuote.map { "Confirm \($0.final_service_charge.formatted(.currency(code: "INR")))" } ?? "Confirm price", style: .dark, isLoading: viewModel.isSubmitting, isDisabled: viewModel.requiresPricingQuote && !viewModel.hasValidQuote) {
                        if viewModel.requiresPricingQuote { showPriceConfirmation = true }
                        else { viewModel.submitJob { success = true } }
                    }.disabled(viewModel.isSubmitting || (viewModel.requiresPricingQuote && !viewModel.hasValidQuote))
                }.padding(16).background(.white)
            }
            .alert("Confirm displayed price?", isPresented: $showPriceConfirmation) {
                Button("Confirm and post", role: .destructive) { viewModel.submitJob { success = true } }
                Button("Review quote", role: .cancel) {}
            } message: {
                Text("Your customer charge is \(viewModel.pricingQuote?.final_service_charge.formatted(.currency(code: "INR")) ?? "unavailable"). The job will use this quote if it remains valid.")
            }
            .navigationDestination(isPresented: $success) { PostJobSuccessView(viewModel: viewModel) }
            .task { await viewModel.loadPricingOptions(); await viewModel.refreshPricingQuote() }
            .onChange(of: viewModel.estimatedDurationHours) { _, _ in Task { await viewModel.refreshPricingQuote() } }
            .onChange(of: viewModel.selectedTime) { _, _ in Task { await viewModel.refreshPricingQuote() } }
            .onChange(of: viewModel.scheduledStartTime) { _, _ in Task { await viewModel.refreshPricingQuote() } }
            .onChange(of: viewModel.isScheduled) { _, _ in Task { await viewModel.refreshPricingQuote() } }
    }

    @ViewBuilder private var quoteBreakdown: some View {
        if let quote = viewModel.pricingQuote {
            VStack(alignment: .leading, spacing: 7) {
                Text("Price breakdown").font(.system(size: 15, weight: .bold))
                priceLine("Base price", quote.base_price)
                Text("Time multiplier: \(quote.time_multiplier.description)×").font(.system(size: 13))
                Text("Demand multiplier: \(quote.demand_multiplier.description)×").font(.system(size: 13))
                priceLine("Raw price", quote.raw_price)
                priceLine("Maximum price", quote.maximum_price)
                priceLine("Final customer payable", quote.final_service_charge, bold: true)
                expiryText(quote.expires_at)
            }.padding(14).frame(maxWidth: .infinity, alignment: .leading).background(Color.errnoBackground, in: RoundedRectangle(cornerRadius: 12))
        } else if viewModel.requiresPricingQuote {
            Text(viewModel.isLoadingQuote ? "Requesting backend price quote…" : "No valid quote is available.")
                .font(.system(size: 13)).foregroundColor(Color.errnoError)
        }
    }

    @ViewBuilder private func expiryText(_ value: String) -> some View {
        if let date = Self.parseISODate(value) {
            Text("Quote expires \(date.formatted(date: .abbreviated, time: .shortened))")
                .font(.system(size: 12)).foregroundColor(viewModel.hasValidQuote ? Color.errnoTextSecondary : Color.errnoError)
        } else { Text("Quote expiry could not be read. Refresh the quote.").foregroundColor(Color.errnoError).font(.system(size: 12)) }
    }

    private static func parseISODate(_ value: String) -> Date? {
        let formatter = ISO8601DateFormatter(); formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.date(from: value) ?? ISO8601DateFormatter().date(from: value)
    }

    @ViewBuilder private func priceLine(_ title: String, _ value: Decimal, bold: Bool = false) -> some View {
        HStack { Text(title); Spacer(); Text(value.formatted(.currency(code: "INR"))).fontWeight(bold ? .bold : .regular) }.font(.system(size: 13))
    }
}
