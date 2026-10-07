
document.addEventListener("DOMContentLoaded", () => {

    loadDashboardData();

});


async function loadDashboardData() {

    try {

        const response = await fetch(
            "/admin/api/dashboard-data",
            {
                method: "GET",
                headers: {
                    "Accept": "application/json"
                },
                credentials: "same-origin"
            }
        );


        const data = await response.json();


        if (!response.ok || !data.success) {

            throw new Error(
                data.message ||
                "Unable to load dashboard data."
            );

        }


        console.log(
            "Dashboard data:",
            data
        );


        // ====================================================
        // STATISTICS
        // ====================================================

        updateElement(
            "totalStudents",
            data.stats.total_students
        );

        updateElement(
            "todayPresent",
            data.stats.today_present
        );

        updateElement(
            "todayAbsent",
            data.stats.today_absent
        );

        updateElement(
            "attendancePercentage",
            data.stats.attendance_percentage + "%"
        );

        updateElement(
            "totalRecords",
            data.stats.total_records
        );


        // ====================================================
        // TODAY'S ATTENDANCE
        // ====================================================

        updateElement(
            "presentCount",
            data.today_attendance.present
        );

        updateElement(
            "absentCount",
            data.today_attendance.absent
        );

        updateElement(
            "totalCount",
            data.today_attendance.total
        );

        updateElement(
            "presentPercentage",
            data.today_attendance.percentage + "%"
        );


        // ====================================================
        // ATTENDANCE CHART
        // ====================================================

        renderAttendanceChart(
            data.attendance_analysis
        );


        // ====================================================
        // RECENT ATTENDANCE
        // ====================================================

        renderRecentAttendance(
            data.recent_attendance
        );


        // ====================================================
        // TODAY'S CLASSES
        // ====================================================

        renderTodayClasses(
            data.today_classes
        );


    } catch (error) {

        console.error(
            "Dashboard loading error:",
            error
        );

        showDashboardError(
            error.message
        );

    }

}


// ============================================================
// UPDATE ELEMENT
// ============================================================

function updateElement(id, value) {

    const element =
        document.getElementById(id);

    if (element) {

        element.textContent =
            value ?? "0";

    }

}


// ============================================================
// ATTENDANCE CHART
// ============================================================

let attendanceChart = null;


function renderAttendanceChart(data) {

    const canvas =
        document.getElementById(
            "attendanceChart"
        );


    if (!canvas) {
        return;
    }


    const labels =
        data.map(
            item => item.date
        );


    const values =
        data.map(
            item => item.present
        );


    if (attendanceChart) {

        attendanceChart.destroy();

    }


    attendanceChart =
        new Chart(
            canvas,
            {
                type: "line",

                data: {

                    labels: labels,

                    datasets: [
                        {
                            label:
                                "Present",

                            data:
                                values,

                            borderWidth:
                                3,

                            tension:
                                0.35,

                            fill:
                                true
                        }
                    ]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio:
                        false,

                    plugins: {

                        legend: {
                            display: true
                        }

                    },

                    scales: {

                        y: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0
                            }
                        }

                    }

                }

            }
        );

}


// ============================================================
// RECENT ATTENDANCE
// ============================================================

function renderRecentAttendance(rows) {

    const tbody =
        document.getElementById(
            "recentAttendanceBody"
        );


    if (!tbody) {
        return;
    }


    tbody.innerHTML = "";


    if (!rows || rows.length === 0) {

        tbody.innerHTML = `
            <tr>
                <td colspan="6"
                    style="text-align:center;">
                    No attendance records found.
                </td>
            </tr>
        `;

        return;

    }


    rows.forEach(
        (row, index) => {

            const status =
                row.status || "Present";


            const tr =
                document.createElement(
                    "tr"
                );


            tr.innerHTML = `

                <td>
                    ${index + 1}
                </td>

                <td>
                    ${escapeHtml(
                        row.student_name ||
                        "Unknown Student"
                    )}
                </td>

                <td>
                    ${escapeHtml(
                        row.date || "-"
                    )}
                </td>

                <td>
                    ${escapeHtml(
                        row.time || "-"
                    )}
                </td>

                <td>
                    <span class="status-badge ${
                        status.toLowerCase()
                    }">
                        ${escapeHtml(status)}
                    </span>
                </td>

                <td>
                    ${
                        row.photo_url
                        ? `<img
                            src="${escapeHtml(
                                row.photo_url
                            )}"
                            class="attendance-photo"
                            alt="Student"
                           >`
                        : `<span>—</span>`
                    }
                </td>

            `;


            tbody.appendChild(tr);

        }
    );

}


// ============================================================
// TODAY'S CLASSES
// ============================================================

function renderTodayClasses(classes) {

    const container =
        document.getElementById(
            "todayClasses"
        );


    if (!container) {
        return;
    }


    container.innerHTML = "";


    if (!classes || classes.length === 0) {

        container.innerHTML = `
            <div class="empty-state">
                No classes scheduled for today.
            </div>
        `;

        return;

    }


    classes.forEach(
        (item) => {

            const time =
                item.start_time ||
                item.time ||
                "--:--";


            const subject =
                item.subject ||
                item.name ||
                "Class";


            const room =
                item.room ||
                item.classroom ||
                "";


            const div =
                document.createElement(
                    "div"
                );


            div.className =
                "class-item";


            div.innerHTML = `

                <div class="class-time">
                    ${escapeHtml(time)}
                </div>

                <div class="class-info">

                    <strong>
                        ${escapeHtml(subject)}
                    </strong>

                    <span>
                        ${escapeHtml(room)}
                    </span>

                </div>

            `;


            container.appendChild(div);

        }
    );

}


// ============================================================
// HTML ESCAPE
// ============================================================

function escapeHtml(value) {

    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

}


// ============================================================
// ERROR
// ============================================================

function showDashboardError(message) {

    console.error(
        "Dashboard:",
        message
    );

}
