type PrivateFileURL = {
  url: string;
};

export async function openPrivateFile(request: () => Promise<PrivateFileURL>) {
  const popup = window.open("about:blank", "_blank");
  if (!popup) {
    throw new Error("Trình duyệt đã chặn cửa sổ xem CV. Vui lòng cho phép popup và thử lại.");
  }
  popup.opener = null;

  try {
    const { url } = await request();
    popup.location.replace(url);
  } catch (error) {
    popup.close();
    throw error;
  }
}
