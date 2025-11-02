import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Settings from "../pages/Settings";

const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

beforeEach(() => {
  mockFetch.mockClear();
});

it("loads and displays current autonomy level", async () => {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ autonomy_level: "high" }),
  } as Response);

  render(<Settings />);

  await waitFor(() => {
    expect(screen.getByText("High Autonomy")).toBeInTheDocument();
  });
});

it("updates autonomy level and persists to backend", async () => {
  mockFetch
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ autonomy_level: "medium" }),
    } as Response)
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ autonomy_level: "low" }),
    } as Response);

  render(<Settings />);

  const slider = screen.getByRole("slider");
  await userEvent.clear(slider);
  await userEvent.type(slider, "0");

  const saveButton = screen.getByRole("button", { name: "Save" });
  await userEvent.click(saveButton);

  await waitFor(() => {
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/settings/autonomy",
      expect.objectContaining({
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ autonomy_level: "low" }),
      })
    );
  });

  expect(screen.getByText("Low Autonomy")).toBeInTheDocument();
});
