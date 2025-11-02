from flask import Flask, render_template
from flask_socketio import SocketIO
from scheduler import Process, fcfs_scheduler_optimized, multi_level_queue_scheduler, sjf_preemptive_scheduler, rr_scheduler

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')



@socketio.on('start_simulation')
def handle_simulation(data):
    processes_data = data['processes']
    algorithm = data['algorithm']
    
    # Adicionamos a leitura dos novos parâmetros
    quantum = data.get('quantum', 0) # Pega o quantum, default 0
    
    # Criamos os processos, agora passando a prioridade
    processes = [Process(p['pid'], p['arrival'], p['burst'], p.get('priority', 0)) for p in processes_data]
    
    scheduler_generator = None
    if algorithm == 'fcfs':
        scheduler_generator = fcfs_scheduler_optimized(processes)
    elif algorithm == 'sjf_preemptive':
        scheduler_generator = sjf_preemptive_scheduler(processes)
    elif algorithm == 'round_robin':
        scheduler_generator = rr_scheduler(processes, int(quantum))
    elif algorithm == 'multi_level':
        scheduler_generator = multi_level_queue_scheduler(processes)
    # ===================================

    if scheduler_generator:
        for state in scheduler_generator:
            if 'final_stats' in state:
                
                stats = state['final_stats']
                if not stats:
                   
                    socketio.emit('simulation_end', {'stats': [], 'avg_wait': 0, 'avg_turnaround': 0})
                    return

                avg_wait = sum(p['waiting_time'] for p in stats) / len(stats)
                avg_turnaround = sum(p['turnaround_time'] for p in stats) / len(stats)
                socketio.emit('simulation_end', {'stats': stats, 'avg_wait': avg_wait, 'avg_turnaround': avg_turnaround})
            else:
                socketio.emit('simulation_update', state)
                socketio.sleep(0.7)

if __name__ == '__main__':
    socketio.run(app, debug=True)