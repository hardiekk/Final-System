function deleteAttendance(idx) {
  console.log("Deleting row:", idx); // debug log
  if (confirm("Delete this entry?")) {
    fetch("/delete_attendance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index: idx })
    })
    .then(res => res.json())
    .then(data => {
      console.log("Response:", data); // debug log
      if (data.success) {
        alert("Deleted!");
        window.location.reload();
      } else {
        alert("Delete failed!");
      }
    })
    .catch(err => {
      alert("Error: " + err.message);
      console.error(err);
    });
  }
}
